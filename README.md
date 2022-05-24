# via-utils

[WIP] Collection of scripts for dealing with VIA project files. Currently supports

- WebVTT -> Subtitle Annotation project
- ...

## Pre-requisites

1. Python3.8+

## (One time) Setup

```bash
python3 -m venv env
./env/bin/pip install -r requirements.txt

# Activate the environment
source env/bin/activate
```


## WebVTT -> Subtitle Annotation

```bash
python3 via.py \
    VIDEO_URL \
    SEGMENT_VTT \
    {--num-splits NUM_SPLITS | --num-segments-in-split NUM_SEGMENTS_IN_SPLIT} \
    {--upload-url VPS_SERVER}
```
