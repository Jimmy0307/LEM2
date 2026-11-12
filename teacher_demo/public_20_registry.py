"""20 NEW, distinct, source-attributed public UCI datasets for rule coverage research.

No existing (12/19/44 plus previous seven extreme pilot plus ecommerce 468
and AI4I 601) data are counted as one of these 20 new datasets.

This registry is a feasibility *subset* protocol: each source dataset is
acquired from UCI, a fixed and documented class-stratified sample is selected
before 80/20 splitting, and max 3..6 features are prespecified to keep exact
Classical reduct computationally tractable. This does not benchmark full
high-dimensional or full-million-row performance.

CC BY status should be reconciled against each source before redistributing
source contents; this pilot stores only sampled-data digest and model metrics.
"""
from __future__ import annotations

def spec(uci_id,title,rows,features,mode,domain,trait,
         selected=None,continuous=None,target=None,license="CC BY 4.0",
         url=None,classes="unknown",label_transform=None,notes=""):
    n=len(selected) if selected else int(features)
    if not 1<=n<=6:raise ValueError("Exact reduct pilot limits features to 6")
    v={
      "id":uci_id,"name":title,"cap_rows":rows,"max_features":n,
      "feature_mode":mode,"domain":domain,"research_trait":trait,
      "url":url or f"https://archive.ics.uci.edu/dataset/{uci_id}",
      "source_license_claim":license,"expected_classes":classes,
      "fixed_feature_contract":selected or f"first {n} in UCI source feature order",
      "notes":notes
    }
    if selected:v["feature_columns"]=selected
    if continuous is not None:v["continuous_columns"]=continuous
    if target:v["target_column"]=target
    if label_transform:v["label_transform"]=label_transform
    return v

REGISTRY={
 "bank_marketing":spec(222,"Bank Marketing",1800,6,"EXPLICIT_MIXED","banking","large mixed conversion; class imbalance",
  ["age","job","marital","education","balance","previous"],["age","balance","previous"],"y",
  notes="Exclude duration: call length observed only after outcome; no bank IDs."),
 "adult_income":spec(2,"Adult Income",1800,6,"EXPLICIT_MIXED","labor economics","large mixed; missing categorical; income imbalance",
  ["age","workclass","education","marital_status","occupation","hours_per_week"],["age","hours_per_week"],
  label_transform="adult_income_strip_period",
  notes="Protected attributes omitted: sex, race, native country. Historical income is not normative eligibility."),
 "mushroom":spec(73,"Mushroom",1600,6,"ALL_CATEGORICAL","biology","all discrete; symbolic; missing values",
  classes="2",notes="Do not treat as a real-world mushroom safety classifier."),
 "phishing":spec(327,"Phishing Websites",1600,6,"ALL_CATEGORICAL","cybersecurity","categorical ordinal signals; binary phishing labels",
  classes="2",notes="Historical URL features; not a current security gateway."),
 "spambase":spec(94,"Spambase",1800,6,"ALL_CONTINUOUS","cybersecurity","high-dimensional original; numeric sparse word frequencies",classes="2"),
 "banknote":spec(267,"Banknote Authentication",None,4,"ALL_CONTINUOUS","financial document","four continuous wavelet statistics; near-balanced binary",classes="2"),
 "dry_bean":spec(602,"Dry Bean",1600,6,"ALL_CONTINUOUS","computer vision","seven classes; continuous shape descriptors; high overlap",classes="7"),
 "rice":spec(545,"Rice Cammeo/Osmancik",1600,6,"ALL_CONTINUOUS","computer vision","binary similar grain shapes; correlated continuous",classes="2"),
 "letter":spec(59,"Letter Recognition",1600,6,"ALL_CATEGORICAL","character recognition","26 classes; integer-valued features treated as categories",classes="26",
  notes="Original integer features 0..15 interpreted as discrete for this stress condition."),
 "iris":spec(53,"Iris",None,4,"ALL_CONTINUOUS","biology","tiny balanced three-class continuous",classes="3"),
 "wine":spec(109,"Wine",None,6,"ALL_CONTINUOUS","chemistry","tiny three-class continuous; many attributes in original",classes="3"),
 "breast_diagnostic":spec(17,"Breast Cancer Wisconsin Diagnostic",None,6,"ALL_CONTINUOUS","diagnostic benchmark","small 30-dimensional numeric original; binary",classes="2",
  notes="Public historical diagnostic research only, not clinical deployment."),
 "magic_gamma":spec(159,"MAGIC Gamma Telescope",1800,6,"ALL_CONTINUOUS","physics","large continuous detection; binary signal-vs-background",classes="2"),
 "htru2":spec(372,"HTRU2",1800,6,"ALL_CONTINUOUS","astronomy","rare positive pulsar (~9%); continuous",classes="2"),
 "eeg_eye_state":spec(264,"EEG Eye State",1800,6,"ALL_CONTINUOUS","sensor / IoT","time-ordered EEG signal, binary eye state and sensor shift risk",
  classes="2",notes="EEG records are time-ordered; this feasibility split is randomized, NOT a chronological generalization test. Replaces failed UCI 357 target import."),
 "german_credit":spec(144,"Statlog German Credit",None,6,"EXPLICIT_MIXED","credit risk","mixed nominal and integer; asymmetric cost of misclassification",
  ["attribute1","attribute2","attribute3","attribute4","attribute5","attribute6"],["attribute2","attribute5"],
  notes="Historical credit discrimination risks; do not use to decide real loans."),
 "sonar":spec(151,"Sonar Mines vs Rocks",None,6,"ALL_CONTINUOUS","signal analysis","small-n, high-d 60 features original",classes="2"),
 "haberman":spec(43,"Haberman Survival",None,3,"ALL_CONTINUOUS","health research","306 rows, strong imbalance, tiny n",classes="2",
  notes="Historical medical dataset, research only."),
 "covertype":spec(31,"Covertype",1800,6,"ALL_CONTINUOUS","geospatial","very large original 581012 rows, seven classes, numeric+binary original",classes="7",
  notes="Full 581012 rows are acquired for deterministic fixed subset; actual model fit only 1800 rows."),
 "grid_stability":spec(471,"Electrical Grid Stability Simulated Data",1800,6,"EXPLICIT_MIXED","electrical power system","simulated power-grid stability, multiple UCI target fields; continuous",
  ["tau1","tau2","tau3","tau4","p2","p3"],["tau1","tau2","tau3","tau4","p2","p3"],"stabf",
  classes="2",notes="Predict only categorical stabf from six input predictors. Exclude continuous target stab and derived p1; simulation, not actual utility grid. Replaces unavailable UCI 325 Python import.")
}
if len(REGISTRY)!=20 or len({v["id"] for v in REGISTRY.values()})!=20:raise RuntimeError("Must contain exactly 20 unique new UCI dataset IDs")
