#!/usr/bin/env python3
import os
import functools

import click
import cv2


from pycine.color import color_pipeline, resize
from pycine.raw import read_frames

try:
    # PyQt and pyqtgraph is not required for installing the pycine package
    from pycine.viewer import view_cine
except ImportError:
    pass


def display(image_8bit):
    cv2.imshow("image", image_8bit)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def save(rgb_image, outfile):
    cv2.imwrite(outfile, rgb_image * 255)


def image_post_processing(raw_image, setup, bpp):
    rgb_image = color_pipeline(raw_image, setup=setup, bpp=bpp)

    if setup.EnableCrop:
        rgb_image = rgb_image[
            setup.CropRect.top : setup.CropRect.bottom + 1, setup.CropRect.left : setup.CropRect.right + 1
        ]

    if setup.EnableResample:
        rgb_image = cv2.resize(rgb_image, (setup.ResampleWidth, setup.ResampleHeight))
    return rgb_image


@click.command()
@click.option("--file-format", default=".png", type=click.Choice([".png", ".jpg", ".tif"]))
@click.option("--start-frame", default=1, type=click.INT)
@click.option("--count", default=1, type=click.INT)
@click.argument("cine_file", type=click.Path(exists=True, readable=True, dir_okay=False, file_okay=True))
@click.argument("out_path", required=False, type=click.Path(exists=True, dir_okay=True, file_okay=False))
@click.version_option()
def cli(file_format, start_frame, count, out_path, cine_file):
    image_gen, setup, bpp = read_frames(cine_file, start_frame=start_frame, count=count)
    image_gen.post_processing = functools.partial(image_post_processing, setup=setup, bpp=bpp)

    if not out_path:
        # visualise cine count is not used here
        if "view_cine" in globals():
            view_cine(image_gen)
        else:
            display(resize(next(image_gen), 720))
        return

    for i, rgb_image in enumerate(image_gen):
        frame = start_frame + i

        ending = file_format.strip(".")
        name = os.path.splitext(os.path.basename(cine_file))[0]
        out_name = "{}-{:06d}.{}".format(name, frame, ending)
        out_file = os.path.join(out_path, out_name)
        print("Writing File {}".format(out_file))
        save(rgb_image, out_file)


if __name__ == "__main__":
    cli()
