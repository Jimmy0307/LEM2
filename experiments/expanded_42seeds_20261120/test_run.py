from copy import deepcopy
import pytest
from experiments.expanded_42seeds_20261120.run import selected_registry,validate_record,SEEDS,SCENARIOS,VARIANTS,POLICIES

def record(scenario='FED_A05'):
    rows=[dict(dataset='UCI20:iris',seed=42,system='FEDERATED',client_count=3,dirichlet_alpha=.5,
               rule_variant=v,selection_policy=p) for v in VARIANTS for p in POLICIES]
    return {'rows':rows,'timing':{'dataset':'UCI20:iris','seed':42,'scenario':scenario}}

def test_frozen_scope_has_188_eligible_and_24_explicit_duplicates():
    full,chosen=selected_registry()
    assert len(chosen)==188
    assert len(full[full.status=='EXCLUDED_SAME_SOURCE'])==24
    assert len(chosen)*len(SEEDS)*len(SCENARIOS)*len(VARIANTS)*len(POLICIES)==379008

@pytest.mark.parametrize('mutation',['duplicate','seed','scenario','clients','alpha','timing'])
def test_checkpoint_rejects_mispaired_or_incomplete_result(mutation):
    data=deepcopy(record())
    if mutation=='duplicate': data['rows'][0]=data['rows'][1].copy()
    if mutation=='seed': data['rows'][0]['seed']=1
    if mutation=='scenario': data['rows'][0]['system']='CENTRALIZED'
    if mutation=='clients': data['rows'][0]['client_count']=5
    if mutation=='alpha': data['rows'][0]['dirichlet_alpha']=.1
    if mutation=='timing': data['timing']['scenario']='FED_IID'
    with pytest.raises(ValueError):validate_record(data,'UCI20:iris',42,'FED_A05')

def test_valid_checkpoint():
    validate_record(record(),'UCI20:iris',42,'FED_A05')
