import random
import string
from typing import List
from urllib.parse import urljoin

from models.via import (
    VIA3_ANNOTATION,
    VIA3_FILE_SOURCE_TYPE,
    VIA3_FILE_TYPE,
    VIA_ATTRIBUTE,
    VIA_CONFIG,
    VIA_FILE,
    VIA_METADATA,
    VIA_PROJECT,
    VIA_VIEW,
)

import requests
import webvtt

CHARS = string.ascii_letters + string.digits
VPS_ENDPOINT = "/via/store/3.x.y/"


def get_random_string(length=6, prefix=""):
    _prefix = f"{prefix}_" if prefix != "" else ""
    return f'{_prefix}{"".join(random.choices(CHARS, k=length))}'


def convert_webvtt_to_via_subtitle_metadata(
    captions, vid: str, subtitle_aid: str
) -> List[VIA_METADATA]:
    """
    Function to convert webvtt captions to VIA_METADATA
    The VIA_METADATA can be used in a subtitle annotation via project
    """
    metadata = [
        VIA_METADATA(
            vid=vid,
            z=[round(caption.start_in_seconds, 3), round(caption.end_in_seconds, 3)],
            xy=[],
            av={subtitle_aid: caption.text},
        )
        for caption in captions
    ]
    return metadata


def create_video_fragments(video, splits):
    return [f"{video}#t={x},{y}" for (x, y) in splits]


def create_shared_project(project, url):
    r = requests.post(
        url, data=project.json(), headers={"Content-Type": "application/json"}
    )
    r.raise_for_status()

    return r.json()


def get_split_ts(captions, segments_per_split):

    split_ts = []
    num_splits = (len(captions) + segments_per_split - 1) // segments_per_split
    for i in range(num_splits):
        ostart = i * segments_per_split
        oend = (i + 1) * segments_per_split

        _segment = captions[ostart:oend]

        tstart = round(_segment[0].start_in_seconds, 3)
        tend = round(_segment[-1].end_in_seconds, 3)

        split_ts.append([tstart, tend])

    return split_ts


def get_via_subtitle_project(video: str, captions, segments_per_split=-1):

    if segments_per_split == -1:
        segments_per_split = len(captions)

    # Config
    via_config = VIA_CONFIG()
    via_config.ui = {
        "file_content_align": "center",
        "file_metadata_editor_visible": True,
        "spatial_metadata_editor_visible": True,
        "spatial_region_label_attribute_id": "",
        "gtimeline_visible_row_count": "4",
    }

    # Attribute
    subtitle_aid = "1"
    via_attribute = {
        subtitle_aid: VIA_ATTRIBUTE(
            aname="subtitle",
            anchor_id="FILE1_Z2_XY0",
            type=1,
            desc="subtitle text",
        )
    }

    # File
    FID = "1"
    _, fname = video.rsplit("/", 1)
    fname, *_ = fname.split("#", 1)

    # Get video fragments
    splits = get_split_ts(captions, segments_per_split)
    video_fragments = create_video_fragments(video, splits)

    # Create file splits
    via_file_splits = [
        {
            FID: VIA_FILE(
                fid=FID,
                fname=fname,
                type=VIA3_FILE_TYPE.VIDEO,
                loc=VIA3_FILE_SOURCE_TYPE.URIHTTP,
                src=_video_src,
            )
        }
        for _video_src in video_fragments
    ]

    # View
    VID = "1"
    via_view = {VID: VIA_VIEW(fid_list=[FID])}

    # Project
    via_project = VIA_PROJECT(
        pname="Unnamed VIA Project",
        creator="https://github.com/IMG-PRCSNG/via-utils",
        data_format_version="3.1.1",
        vid_list=[VID],
    )

    # Convert captions to subtitle metadata
    via_metadata = {
        get_random_string(8, VID): x
        for x in convert_webvtt_to_via_subtitle_metadata(captions, VID, subtitle_aid)
    }

    # VIA Annotation
    return [
        VIA3_ANNOTATION(
            project=via_project,
            config=via_config,
            attribute=via_attribute,
            file=f,
            view=via_view,
            metadata=via_metadata,
        )
        for f in via_file_splits
    ]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Accept the source
    parser.add_argument("video", help="Source video")

    # Accept webvtt file
    parser.add_argument("vtt", type=str, help="WebVTT file to convert to VIA Project")

    # Splits
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--num-segments-in-split",
        type=int,
        default=-1,
        help="Number of segments in each split",
    )
    group.add_argument(
        "--num-splits", type=int, default=1, help="Number of splits to make"
    )

    # Accept timestamps for split
    # parser.add_argument(
    #     "--splits", nargs="+", default=[], help="timestamps to split the project at"
    # )

    # Upload to VPS
    parser.add_argument("--upload-url", help="VPS URL to upload projects")

    args = parser.parse_args()

    # Read captions from webvtt
    captions = webvtt.read(args.vtt)

    n_segments = args.num_segments_in_split
    if args.num_splits:
        n_segments = len(captions) // args.num_splits

    # Create VIA Project
    via_annotations = get_via_subtitle_project(args.video, captions, n_segments)

    upload_url = None
    if args.upload_url:
        upload_url = urljoin(args.upload_url, VPS_ENDPOINT)

    for i, v in enumerate(via_annotations, start=1):
        output_filename = f"output/{i}.json"
        if upload_url:
            try:
                response = create_shared_project(v, upload_url)
                output_filename = f'output/{response["pid"]}.json'
            except Exception as e:
                print(f"Shared project creation failed ({i})", e)

        with open(output_filename, "w") as f:
            f.write(v.json(indent=2))
