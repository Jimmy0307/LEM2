"""Twelve additional publicly attributed UCI classification domains, disjoint from prior 20+9.

Pilot = one seed 42, two architectures, fixed <=6 features, reproducible sampling.
License is a source-record claim, NOT a universal claim for other datasets.
Only metadata and reproducible prepared subset are published after validating
the upstream source and sample; deployment uses are excluded.
"""
from __future__ import annotations
from teacher_demo.public_20_registry import spec,REGISTRY as PREVIOUS20
from teacher_demo.extreme_dataset_runner import REGISTRY as PREVIOUS_EXTRA
REGISTRY={
 "ionosphere":spec(52,"Ionosphere Radar Return",None,6,"ALL_CONTINUOUS","radar / physics",
     "351 cases, 34 raw continuous features, binary radar validity",classes="2",notes="First six features; no claimed full 34-feature performance."),
 "yeast_localization":spec(110,"Yeast Protein Localization",1200,6,"ALL_CONTINUOUS","bioinformatics",
     "Ten-class protein localization, class imbalance and rare classes",classes="10",
     notes="Original 8 numeric features; sample 1200, 6 predefined first features."),
 "image_segmentation":spec(50,"Image Segmentation",1400,6,"ALL_CONTINUOUS","computer vision",
     "Seven regional image labels from 3x3 image regions; potential shared-image leakage",classes="7",
     notes="Original images produce multiple observations; random split can cause correlated train-test records."),
 "vehicle_silhouettes":spec(149,"Statlog Vehicle Silhouettes",None,6,"ALL_CONTINUOUS","machine vision",
     "Four classes and 18 extracted shape attributes; orientation shift sensitivity",classes="4",
     notes="Raw features integers interpreted continuous, not categorical, for this declared experiment."),
 "wheat_seeds":spec(236,"Wheat Seeds",None,6,"ALL_CONTINUOUS","agri-tech",
     "210 rows, three equally sized wheat kernel types and seven continuous measurements",classes="3"),
 "raisin_grains":spec(850,"Raisin Morphology",None,6,"ALL_CONTINUOUS","agri-tech",
     "900 rows, two balanced visual grain varieties and continuous shape features",classes="2"),
 "wine_quality_ordinal_to_binary":spec(186,"Wine Quality (binary>=6 protocol)",1600,6,"ALL_CONTINUOUS","quality / operations",
     "Originally ordered wine quality labels; explicit secondary BINARY >=6 target task",classes="2",
     target="quality",label_transform="wine_quality_binary_ge6",
     notes="Original quality ordinal regression/multiclass. We deliberately binarize at >=6 for a separate classification protocol; not original UCI target classes."),
 "qsar_biodegradation":spec(254,"QSAR Biodegradation",None,6,"ALL_CONTINUOUS","environmental chemistry",
     "1055 chemical records, 41 descriptors in source and two biodegradation classes",classes="2",
     notes="Potential unnamed variables: first six source columns; no structure-model deployment."),
 "vertebral_column":spec(212,"Vertebral Column",None,6,"ALL_CONTINUOUS","medical research",
     "310 rows, six continuous biomechanics variables, possible two-vs-three target variant",classes="unknown",
     notes="UCI may expose alternative 2/3 label protocols; record actual observed class count, do not invent."),
 "student_dropout":spec(697,"Higher-Ed Dropout and Academic Success",1800,6,"ALL_CATEGORICAL","education / retention",
     "4424 records, three classes, 36 source predictors; pre-enrollment coded attributes only",classes="3",
     target="target",
     notes="First six predictors treated as coded nominal categories; NO first/second semester outcome features used."),
 "blood_donation":spec(176,"Blood Transfusion Service Center",None,4,"ALL_CONTINUOUS","services / RFM",
     "Taiwan donor retention 748 records, RFM/T numeric and 24% positive",classes="2",
     notes="Public source of donation history, not individual identification; no deployment."),
 "fertility":spec(244,"Fertility",None,6,"ALL_CONTINUOUS","medical research",
     "100 volunteers, rare binary outcome and small sample instability",classes="2",
     notes="Only research; privacy and clinical validity cannot be inferred from toy sample.")
}
if len(REGISTRY)!=12:raise AssertionError("Must have exactly twelve new sources")
ids={cfg["id"] for cfg in REGISTRY.values()}
assert len(ids)==len(REGISTRY)
assert not ids & {cfg["id"] for cfg in PREVIOUS20.values()}
assert not ids & {cfg["id"] for cfg in PREVIOUS_EXTRA.values()}
