# Ultralytics YOLO 🚀, GPL-3.0 license

import hydra
import torch

from ultralytics.yolo.engine.predictor import BasePredictor
from ultralytics.yolo.engine.result import Result
from ultralytics.yolo.utils import DEFAULT_CONFIG, ROOT
from ultralytics.yolo.utils.plotting import Annotator


class ClassificationPredictor(BasePredictor):

    def get_annotator(self, img):
        return Annotator(img, example=str(self.model.names), pil=True)

    def preprocess(self, img):
        img = (img if isinstance(img, torch.Tensor) else torch.Tensor(img)).to(self.model.device)
        img = img.half() if self.model.fp16 else img.float()  # uint8 to fp16/32
        return img

    def postprocess(self, preds, img, orig_img):
        results = []
        for i, pred in enumerate(preds):
            shape = orig_img[i].shape if self.webcam else orig_img.shape
            results.append(Result(probs=pred.softmax(0), orig_shape=shape[:2]))
        return results

    def write_results(self, idx, results, batch):
        p, im, im0 = batch
        log_string = ""
        if len(im.shape) == 3:
            im = im[None]  # expand for batch dim
        self.seen += 1
        im0 = im0.copy()
        if self.webcam:  # batch_size >= 1
            log_string += f'{idx}: '
            frame = self.dataset.cound
        else:
            frame = getattr(self.dataset, 'frame', 0)

        self.data_path = p
        # save_path = str(self.save_dir / p.name)  # im.jpg
        self.txt_path = str(self.save_dir / 'labels' / p.stem) + ('' if self.dataset.mode == 'image' else f'_{frame}')
        log_string += '%gx%g ' % im.shape[2:]  # print string
        self.annotator = self.get_annotator(im0)

        result = results[idx]
        if len(result) == 0:
            return log_string
        prob = result.probs
        # Print results
        top5i = prob.argsort(0, descending=True)[:5].tolist()  # top 5 indices
        log_string += f"{', '.join(f'{self.model.names[j]} {prob[j]:.2f}' for j in top5i)}, "

        # write
        text = '\n'.join(f'{prob[j]:.2f} {self.model.names[j]}' for j in top5i)
        if self.args.save or self.args.show:  # Add bbox to image
            self.annotator.text((32, 32), text, txt_color=(255, 255, 255))
        if self.args.save_txt:  # Write to file
            with open(f'{self.txt_path}.txt', 'a') as f:
                f.write(text + '\n')

        return log_string


@hydra.main(version_base=None, config_path=str(DEFAULT_CONFIG.parent), config_name=DEFAULT_CONFIG.name)
def predict(cfg):
    cfg.model = cfg.model or "yolov8n-cls.pt"  # or "resnet18"
    cfg.source = cfg.source if cfg.source is not None else ROOT / "assets"
    predictor = ClassificationPredictor(cfg)
    predictor(verbose=True)


if __name__ == "__main__":
    predict()
