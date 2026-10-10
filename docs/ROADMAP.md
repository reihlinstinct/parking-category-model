# Roadmap

Goal: suggest the right report category from a photo, with a person always confirming. The model
never files anything.

## Stage 1 - now: suggest from the photo, a person confirms

- The reporting tool picks a category for each photo and drafts the Hebrew text from the
  templates in `labels.json`.
- A person confirms or corrects the category before anything is filed.
- No model is trained at this stage. The suggestion comes from an existing general-purpose vision model.
  This is the baseline that later stages must beat.

## Stage 2 - every confirmed report becomes a label

- When a person confirms a report, the private data location records one manifest row: image hash,
  confirmed class id, and whether the person changed the suggestion.
- The manifest points to the stored photo. Photos are never duplicated and never leave the private location.
- Duplicate photos are skipped by hash. Corrections are the most valuable rows, so they are kept
  with the original suggestion.

## Stage 3 - train a classifier at about 300 labeled photos

- Start when there are roughly 300 confirmed photos, with at least 30 per class that will be modeled.
  Classes with fewer photos stay with the baseline.
- Train with `parking_category_model.train` on a private machine. Hold out a validation set
  chosen by hash, not by time, so near-duplicates do not leak across the split.
- Compare against the Stage 1 baseline on the same held-out photos.
- Replace the baseline only if the trained model is better on the metrics below. Otherwise keep the baseline
  and collect more labels.
- Export to TFLite for the mobile apps. Weights stay private.

## Evaluation metrics

- Overall accuracy and per-class precision, recall and F1 (`metrics.py`).
- Confusion matrix, to see which classes get mixed up (sidewalk vs. red-white curb, crosswalk vs. sidewalk).
- Precision on the sidewalk class matters most: a wrong confident suggestion costs a person's time.
- Share of predictions below a confidence threshold that are sent to a person with no suggestion.
- Rate of corrections by a person after the model is in use. This is the real-world metric.

## Privacy rules

See [PRIVACY.md](PRIVACY.md). In short: this repo holds code only; photos, labels and weights stay
private; CI blocks images, weights, plates, GPS, addresses and keys; issues and PRs carry no real report details.

## Open items

- Confirm the 106 code for blocked curb ramps and for the "other" class (`unverified` in `labels.json`).
- Decide the confidence threshold with real data.
