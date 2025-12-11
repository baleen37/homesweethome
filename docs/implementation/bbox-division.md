# Bounding Box Division Implementation

## Overview
To overcome the 600 POI limit in `/api/v2/pois-bounding`, we implement automatic bounding box division.

## Algorithm
1. Make initial request with full bbox
2. If exactly 600 results returned, divide bbox into 2x2 grid
3. Request each sub-bbox sequentially
4. Aggregate all results

## Example
```python
# Dense area like Gangnam-gu
bbox = {"startX": 127.04, "endX": 127.12, "startY": 37.48, "endY": 37.52}
divided = crawler._divide_bounding_box(bbox)  # Returns 4 boxes
```

## Performance Impact
- Increases API calls from 1 to 4 for dense areas
- Total time increases proportionally (4x with rate limiting)
- Necessary for complete data collection in dense areas
