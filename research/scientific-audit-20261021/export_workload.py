#!/usr/bin/env python3
"""Audit one executed, fixed-shape residual feed-forward block. CPU float32 only."""
import hashlib,json,platform,sys
from pathlib import Path
import torch
from torch import nn
from torch.fx import Interpreter,symbolic_trace
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from verifier import MODEL,validate_graph,digest
OUT=Path(__file__).resolve().parent

class ResidualMLP(nn.Module):
    def __init__(self):
        super().__init__();self.up=nn.Linear(64,256,bias=False);self.relu=nn.ReLU();self.down=nn.Linear(256,64,bias=False);self.out=nn.ReLU()
    def forward(self,x):return self.out(self.down(self.relu(self.up(x)))+x)

def storage(t):return t.untyped_storage().data_ptr()
def desc(t):return {'shape':list(t.shape),'stride':list(t.stride()),'bytes':t.numel()*t.element_size(),'storage_bytes':t.untyped_storage().nbytes(),'contiguous':t.is_contiguous(),'offset':t.storage_offset()}

def main():
    torch.manual_seed(20261021);torch.set_num_threads(1)
    model=ResidualMLP();x=torch.randn(8,64,requires_grad=True);gm=symbolic_trace(model)
    values={};saved=[];current=[None];parameters={storage(p):name for name,p in model.named_parameters()}
    class Audit(Interpreter):
        def run_node(self,n):
            current[0]=n.name;value=super().run_node(n)
            if isinstance(value,torch.Tensor) and n.op!='output':values[n.name]=value
            return value
    def pack(t):saved.append((current[0],t));return t
    with torch.autograd.graph.saved_tensors_hooks(pack,lambda t:t):y=Audit(gm).run(x)
    y.sum().backward();grads={k:p.grad.detach().clone() for k,p in model.named_parameters()};xgrad=x.grad.clone()
    model.zero_grad();x.grad=None;model(x).sum().backward()
    assert torch.equal(xgrad,x.grad)
    assert all(torch.equal(grads[k],p.grad) for k,p in model.named_parameters())
    # Direct matrix calculus VJP, separate from autograd and saved-tensor hooks.
    with torch.no_grad():
        z=x@model.up.weight.T;h=z.clamp_min(0);pre=h@model.down.weight.T+x
        dout=(pre>0).float();dz=(dout@model.down.weight)*(z>0).float()
        manual={'up.weight':dz.T@x,'down.weight':dout.T@h}
        torch.testing.assert_close(xgrad,dz@model.up.weight+dout,rtol=1e-5,atol=1e-6)
        for k in grads:torch.testing.assert_close(grads[k],manual[k],rtol=1e-5,atol=1e-6)
    activations={storage(t):name for name,t in values.items()}
    assert len(activations)==len(values), 'aliasing activation outputs needs a new model'
    assert all(t.is_contiguous() and t.storage_offset()==0 and t.untyped_storage().nbytes()==t.numel()*t.element_size() for t in values.values())
    requirements={name:set() for name in values};save_rows=[]
    for owner,t in saved:
        key=storage(t)
        if key in parameters:kind='parameter';name=parameters[key]
        elif key in activations:
            kind='activation';name=activations[key];requirements[owner].add(name)
        else:raise ValueError(f'unmodeled saved storage at {owner}: {desc(t)}')
        save_rows.append({'owner':owner,'class':kind,'name':name,**desc(t)})
    expected={'up':['x'],'relu':['relu'],'down':['relu'],'add':[],'out':['out']}
    nodes=[]
    for n in gm.graph.nodes:
        if n.op in ('placeholder','output'):continue
        req=sorted(requirements[n.name]);assert req==expected[n.name],(n.name,req)
        nodes.append({'id':n.name,'deps':[v.name for v in n.all_input_nodes],'bytes':desc(values[n.name])['bytes'],'cost':1,'backward_cost':1,'recomputable':True,'backward_requires':req,'kind':str(n.target)})
    g=validate_graph({'model':MODEL,'id':'exported-residual-mlp-8x64x256-v1','inputs':[{'id':'x','bytes':2048}],'nodes':nodes,'outputs':['out'],'provenance':{'source':'Executed ResidualMLP in export_workload.py','seed':20261021,'torch':torch.__version__,'shape':[8,64],'hidden_width':256,'dtype':'float32','cost_unit':'one forward operator invocation; not FLOPs or elapsed time','scope':'Distinct logical operator outputs and saved activation dependencies. Excludes parameters, gradients, backward temporaries, allocator/workspaces; not hardware peak memory.'}})
    # Hand-computed sizes: 8*64*4=2048 and 8*256*4=8192.
    assert [n['bytes'] for n in nodes]==[8192,8192,2048,2048,2048]
    (OUT/'graph.json').write_text(json.dumps(g,indent=2)+'\n')
    (OUT/'fx-graph.txt').write_text(str(gm.graph)+'\n')
    exported=torch.export.export(model,(x,));(OUT/'aten-graph.txt').write_text(str(exported.graph)+'\n')
    report={'status':'PASS','evidence_level':'author-checked; independent review pending','torch':torch.__version__,'python':platform.python_version(),'platform':platform.platform(),'seed':20261021,'threads':1,'graph_sha256':digest(g),'distinct_contiguous_activation_storages':True,'hooked_vs_unhooked_gradients_exact':True,'direct_matrix_calculus_gradients_match':True,'hand_checked_backward_requirements':expected,'activations':{k:desc(v) for k,v in values.items()},'saved_tensors':save_rows,'parameter_bytes_excluded':sum(p.numel()*p.element_size() for p in model.parameters()),'limitations':['One bias-free residual feed-forward block, not a production model suite.','FX operator-level trace includes Linear as one operator; ATen export is also retained.','No claim that an optimized abstract schedule is executed by autograd.','No GPU or total training peak measurement; backward and intra-operator temporaries excluded.']}
    (OUT/'export-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
