from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional, Protocol, Tuple, Union

import torch
from skimage.segmentation import quickshift


class Tasktype(Enum):
    """
    Type of data that is going to be explained by the
    anchor.
    """

    TABULAR = auto()
    IMAGE = auto()
    TEXT = auto()


class Sampler:
    """
    Abstract Sampler that is used as a factory for its 
    subclasses. Use create(Tasktype) to initialise sub-
    classes for each task.
    """

    subclasses = {}

    def __init_subclass__(cls, **kwargs):
        """
        Registers every subclass in the subclass-dict.
        """
        super().__init_subclass__(**kwargs)
        cls.subclasses[cls.type] = cls

    @classmethod
    def create(cls, type: Tasktype, input: any, predict_fn: Callable, **kwargs):
        """
        Creates subclass depending on typ.

        Args:
            typ: Tasktype 
        Returns:
            Subclass that is used for the given Tasktype.
        """
        if type not in cls.subclasses:
            raise ValueError("Bad message type {}".format(type))

        return cls.subclasses[type](
            input, predict_fn, **kwargs
        )  # every sampler needs input and predict function


class TabularSampler(Sampler):
    type: Tasktype = Tasktype.TABULAR

    def sample(
        self, input: any, predict_fn: Callable[[any], torch.Tensor]
    ) -> torch.Tensor:
        ...


class ImageSampler(Sampler):
    type: Tasktype = Tasktype.IMAGE

    def __init__(self, input: any, predict_fn: Callable[[any], torch.Tensor], **kwargs):
        assert input.shape[2] == 3

        self.label = torch.argmax(predict_fn(input.permute(2, 0, 1).unsqueeze(0))[0])
        # run segmentation on the image
        self.segments = torch.from_numpy(
            quickshift(input.double(), kernel_size=4, max_dist=200, ratio=0.2)
        )  # parameters from original implementation
        segment_features = torch.unique(self.segments)
        self.n_features = len(segment_features)

        # create superpixel image by replacing superpixels by its mean in the original image
        self.sp_image = torch.clone(input)
        for spixel in segment_features:
            self.sp_image[self.segments == spixel, :] = torch.mean(
                self.sp_image[self.segments == spixel, :], axis=0
            )
        self.image = input
        self.predict_fn = predict_fn

    def sample(
        self, present: torch.Tensor, num_samples: int
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Sample function for image data.
        Generates random image samples from the distribution around the original image.
        Features can be blocked from replacement with the present attribute.
        """
        data = torch.randint(
            0, 2, (num_samples, self.n_features)
        )  # generate random feature mask for each sample
        data[:, present] = 1  # set present features to one
        samples = torch.stack([self.__generate_image(mask) for mask in data])
        preds = self.predict_fn(samples.permute(0, 3, 1, 2))
        preds_max = torch.argmax(preds, axis=1)
        labels = (preds_max == self.label).int()

        return self.segments, data, labels

    def __generate_image(self, feature_mask: torch.Tensor) -> torch.Tensor:
        """
        Generate sample image given some feature mask.
        The true image will get permutated dependent on the feature mask.
        Pixel which are outmasked by the mask are replaced by the correspodning superpixel pixel.
        """
        img = self.image.clone()
        zeros = torch.where(feature_mask == 0)[0]
        mask = torch.zeros(self.segments.shape).bool()
        for z in zeros:
            mask[self.segments == z] = True
        img[mask] = self.sp_image[mask]

        return img


class TextSampler(Sampler):
    type: Tasktype = Tasktype.TEXT

    def sample(
        self, input: any, predict_fn: Callable[[any], torch.Tensor]
    ) -> torch.Tensor:
        ...


@dataclass(frozen=True)
class Anchor:
    """
    Approach to explain predictions of a blackbox model using anchors.
    It returns the explaination with a precision and coverage score.

    More details can be found in the following paper:
    https://homes.cs.washington.edu/~marcotcr/aaai18.pdf
    """

    tasktype: Tasktype
    sampler: Sampler = field(init=False)
    verbose: bool = False

    def explain_instance(self, input: any, predict_fn: Callable[[any], torch.Tensor]):
        self.sampler = Sampler.create(self.tasktype, input, predict_fn)
        exp = self.__greedy_anchor(self.sampler.sample)

    def __greedy_anchor(
        sample_fn: Callable,
        delta: float = 0.05,
        epsilon: float = 0.1,
        batch_size: int = 16,
    ):
        ...

    def beam_anchor():
        ...