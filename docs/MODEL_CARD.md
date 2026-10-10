# Model card (template)

**Task:** classify a street photo of a parking problem into one report category.

**Classes and codes:** see `src/parking_category_model/labels.json`. Each class has a `code_status`:
`verified` (confirmed to work), `fallback` (mapped to the nearest existing code, text carries the detail),
`unverified` (no confirmed code yet; a person must choose before filing).

**Architecture:** MobileNetV3-Small, ImageNet-pretrained, frozen base, small classification head,
light augmentation. Input 224x224 RGB. Exported to TFLite (float16).

**Intended use:** suggest a category and a draft text that a person reviews. The model never files
anything. Low-confidence or `unverified` predictions must go to a person.

**Not for:** identifying people or vehicles, automatic enforcement, or filing without review.

**Data:** private; not distributed with this repo. When publishing a trained model, fill in: number of
images per class, collection period, split method, and results from `parking_category_model.evaluate`
(per-class precision, recall, confusion matrix).

**Known limits:** small, single-city data will bias toward local street types; crosswalk and ramp
classes are likely under-represented; night and rain photos need extra checking.
