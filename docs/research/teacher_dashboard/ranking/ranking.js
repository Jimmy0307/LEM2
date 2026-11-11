"use strict";
const $=id=>document.getElementById(id),ns="http://www.w3.org/2000/svg";
const POLICIES=["FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH","POPULATION_STANDARD","POPULATION_GLOBAL"];
const names={FIRST_MATCH:"FIRST",SIMPLE_VOTING:"SIMPLE",STANDARD_VOTING:"STD",GLOBAL_STRENGTH:"GS",POPULATION_STANDARD:"PS",POPULATION_GLOBAL:"PG"};
const METRICS=["accuracy","balanced_accuracy","macro_f1","conflict_resolution_accuracy","conflict_case_rate","coverage"];
const structural=new Set(["conflict_case_rate","coverage"]);
const COLORS=["#11867b","#4e83ad","#b88549","#8b76ab","#ce6e6e","#7a9672"];
let rows=[],summary=[],chosen=null;
const pct=x=>x==null||!Number.isFinite(x)?"—":(x*100).toFixed(2)+"%";
const pp=x=>x==null||!Number.isFinite(x)?"—":(x*100).toFixed(2)+" pp";
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function avg(xs){return xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:null;}
function std(xs){const a=avg(xs);return xs.length&&a!=null?Math.sqrt(avg(xs.map(x=>(x-a)**2))):null;}
function parsed(x){return x==null||!Number.isFinite(+x)?null:Number(x);}
function asSVG(tag,attrs={},txt){const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(txt!==undefined)n.textContent=txt;return n;}
function t(svg,x,y,txt,attrs={}){svg.append(asSVG("text",{x,y,"font-size":"12",fill:"#556b75",...attrs},txt));}
function configName(o){return(o.client_count===0?"Centralized":"Federated C"+o.client_count)+(o.selection_policy?" · "+(names[o.selection_policy]||o.selection_policy):"");}
function measures(ds,arch,pol){
 const d=rows.filter(r=>r.split_mode==="HOLDOUT_80_20"&&r.selection_policy===pol&&(ds==="ALL"||r.dataset===ds)&&(arch==="ALL"||r.system===arch));
 const outputs=[];
 for(const c of [0,2,3,4,5]){
  const sample=d.filter(r=>Number(r.client_count)===c);
  if(!sample.length)continue;
  const bySeed=Array.from({length:42},(_,i)=>{
   const r=sample.filter(z=>Number(z.seed)===i+1);
   return Object.fromEntries(METRICS.map(k=>[k,avg(r.map(z=>parsed(z[k])).filter(v=>v!==null))]));
  });
  const scores=Object.fromEntries(METRICS.map(k=>[k,avg(bySeed.map(s=>s[k]).filter(v=>v!==null))]));
  const sds=Object.fromEntries(METRICS.map(k=>[k,std(bySeed.map(s=>s[k]).filter(v=>v!==null))]));
  outputs.push({client_count:c,system:c?"FEDERATED":"CENTRALIZED",selection_policy:pol,scores,sds,bySeed});
 }
 return outputs;
}
function allStats(ds,arch,policy){
 let out=[];
 for(const p of POLICIES){
  if(policy!=="ALL"&&p!==policy)continue;
  out.push(...measures(ds,arch,p));
 }
 return out;
}
function order(metric){return metric==="conflict_case_rate"?-1:1;}
function sorted(stats,metric){return [...stats].filter(x=>x.scores[metric]!=null).sort((a,b)=>order(metric)*(b.scores[metric]-a.scores[metric])||configName(a).localeCompare(configName(b)));}
function topLine(o,metric){
 return configName(o)+": "+pct(o.scores[metric])+"，跨 Seed SD "+pp(o.sds[metric]);
}
function winnerUI(list,metric){
 const winner=list[0],second=list[1];
 if(!winner){$("winnerCards").innerHTML="這組條件沒有可排名的實測數據。";return;}
 const lead=winner.scores[metric],gap=second?(lead-second.scores[metric])*order(metric):null;
 const relevant=[
 ["最佳配置",configName(winner),"只比較相同的 80/20 測試協定"],
 ["目標平均分數",pct(lead),"42 Seeds 的配置等權平均"],
 ["優於第二名",gap==null?"—":pp(gap),"未做跨資料集獨立性推論"],
 ["跨 Seed 波動",pp(winner.sds[metric]),"標準差，不是 95% 信賴區間"]
 ];
 $("winnerCards").innerHTML=relevant.map(([title,val,desc])=>'<div class="score-box"><small>'+esc(title)+'</small><strong>'+esc(val)+'</strong><p class="evidence">'+esc(desc)+'</p></div>').join("");
 $("winnerNarrative").innerHTML='<b>解讀：</b>在當前選定資料集下，'+esc(configName(winner))+' 的 '+esc($("objective").selectedOptions[0].textContent)+' 平均為 <b>'+pct(lead)+'</b>。'+(second?('與第二名 '+esc(configName(second))+' 的差距是 '+pp(gap)+'；差距小不代表顯著不同。'):"")+' <b>代價／限制：</b>此配置的 Conflict '+pct(winner.scores.conflict_case_rate)+'，Coverage '+pct(winner.scores.coverage)+'，BA '+pct(winner.scores.balanced_accuracy)+'。'+($("dataset").value==="Hayes-Roth"?" Hayes-Roth 此處仍是原本 132 筆內的重複切分；要看官方 28 筆測試須用下方獨立驗證表。":"");
}
function barChart(list,metric){
 const svg=$("rankingChart");svg.replaceChildren();
 const leaders=list.slice(0,6);if(!leaders.length)return;
 const max=Math.max(.01,...leaders.map(o=>o.scores[metric]||0)),lo=Math.min(0,...leaders.map(o=>o.scores[metric]));
 const domain=metric==="conflict_case_rate"||metric==="coverage"?1:1;
 const x0=310,width=660,top=36,h=52,scale=v=>Math.max(0,Math.min(1,(v-lo)/(domain-lo||1)))*width;
 t(svg,x0,18,"平均分數（條紋誤差線＝Seed 標準差）",{"font-size":13});
 leaders.forEach((o,i)=>{
  const y=top+i*h,score=o.scores[metric],sd=o.sds[metric]||0,w=scale(score);
  t(svg,8,y+23,(i+1)+". "+configName(o),{"font-size":13,fill:"#243f51"});
  svg.append(asSVG("rect",{x:x0,y:y,width:w,height:27,rx:4,fill:COLORS[i]}));
  const xa=x0+scale(Math.max(lo,score-sd)),xb=x0+scale(Math.min(domain,score+sd));
  svg.append(asSVG("line",{x1:xa,y1:y+14,x2:xb,y2:y+14,stroke:"#172e43","stroke-width":3}));
  [xa,xb].forEach(px=>svg.append(asSVG("line",{x1:px,y1:y+8,x2:px,y2:y+20,stroke:"#172e43","stroke-width":2})));
  t(svg,x0+w+8,y+19,pct(score),{fill:"#1d4c59","font-size":14});
 });
}
function table(list,metric){
 const best=list[0]?.scores[metric]??null;
 $("rankTable").innerHTML=list.map((o,i)=>{
 const val=o.scores[metric],delta=best==null?null:Math.abs(best-val);
 return '<tr><td>'+ (i+1)+'</td><td>'+esc(o.client_count===0?"Centralized":"Federated C"+o.client_count)+'</td><td>'+esc(names[o.selection_policy])+'</td><td class="n"><b>'+pct(val)+'</b></td><td class="n">'+pp(o.sds[metric])+'</td><td class="n">'+pct(o.scores.accuracy)+'</td><td class="n">'+pct(o.scores.balanced_accuracy)+'</td><td class="n">'+pct(o.scores.macro_f1)+'</td><td class="n">'+pct(o.scores.conflict_case_rate)+'</td><td class="n">'+pct(o.scores.coverage)+'</td><td class="n">'+pp(delta)+'</td></tr>';
 }).join("");
}
function frontier(list){
 const svg=$("frontier");svg.replaceChildren();
 const coords={x0:80,x1:885,y0:45,y1:379};
 for(let i=0;i<=4;i++){const frac=i/4,xx=coords.x0+frac*(coords.x1-coords.x0),yy=coords.y1-frac*(coords.y1-coords.y0);
   svg.append(asSVG("line",{x1:coords.x0,y1:yy,x2:coords.x1,y2:yy,stroke:"#e0e9ea"}));
   svg.append(asSVG("line",{x1:xx,y1:coords.y0,x2:xx,y2:coords.y1,stroke:"#eff1f1"}));
   t(svg,coords.x0-12,yy+4,(frac*100).toFixed(0)+"%",{"text-anchor":"end"});t(svg,xx,coords.y1+22,(frac*100).toFixed(0)+"%",{"text-anchor":"middle"});
 }
 t(svg,465,430,"Accuracy (高 →)",{fill:"#355f6a","font-size":14});t(svg,25,20,"Balanced Accuracy (高 ↑)",{fill:"#355f6a","font-size":14});
 list.forEach(o=>{
   const x=o.scores.accuracy,y=o.scores.balanced_accuracy;
   if(x==null||y==null)return;
   const px=coords.x0+x*(coords.x1-coords.x0),py=coords.y1-y*(coords.y1-coords.y0);
   const n=asSVG("circle",{cx:px,cy:py,r:o.client_count===0?6:8,fill:COLORS[o.client_count],stroke:"#fff","stroke-width":2,tabindex:0,role:"button","aria-label":configName(o)});
   n.append(asSVG("title",{},configName(o)+" Acc "+pct(x)+" / BA "+pct(y)));
   const act=()=>{
    chosen=o;
    $("selectedConfig").innerHTML='<b>'+esc(configName(o))+'</b>｜Accuracy '+pct(x)+'、BA '+pct(y)+'、Macro-F1 '+pct(o.scores.macro_f1)+'、Coverage '+pct(o.scores.coverage)+'、Conflict '+pct(o.scores.conflict_case_rate)+'。'+
      '跨 Seed Accuracy SD '+pp(o.sds.accuracy)+'；BA SD '+pp(o.sds.balanced_accuracy)+'。比較前應固定資料集和切分協定。';
   };
   n.addEventListener("click",act);
   n.addEventListener("keydown",e=>{if(e.key==="Enter")act();});
   svg.append(n);
 });
}
function champions(){
 const datasets=["Balance Scale","Car Evaluation","Hayes-Roth"];
 const content=datasets.map(ds=>{
 const arr=allStats(ds,"ALL","ALL");
 const a=sorted(arr,"accuracy")[0],b=sorted(arr,"balanced_accuracy")[0],c=sorted(arr,"macro_f1")[0];
 return '<tr><td>'+esc(ds)+'</td><td>'+esc(configName(a))+'</td><td class="n">'+pct(a.scores.accuracy)+'</td><td>'+esc(configName(b))+'</td><td class="n">'+pct(b.scores.balanced_accuracy)+'</td><td>'+esc(configName(c))+'</td><td class="n">'+pct(c.scores.macro_f1)+'</td><td>'+(ds==="Hayes-Roth"?'<span class="pill-warn">重複模式／官方測試待分開驗收</span>':"原始 80/20 重複切分")+'</td></tr>';
 });
 $("datasetChampions").innerHTML=content.join("");
}
function csvParse(t){
 const lines=t.trim().split(/\r?\n/);const h=lines.shift().split(",");
 return lines.map(line=>Object.fromEntries(line.split(",").map((v,i)=>[h[i],v])));
}
async function externalResults(){
 try{
  const response=await fetch("../data/HAYES_HOLDOUT_PROTOCOLS_42SEEDS.csv",{cache:"no-cache"});
  if(!response.ok)throw Error("尚未有 42 Seeds 完整通過證據");
  const d=csvParse(await response.text());
  if(d.length!==2520||new Set(d.map(x=>x.seed)).size!==42)throw Error("資料組合尚未完成");
  const best=[];
  for(const protocol of ["UCI_OFFICIAL_132_28","GROUP_HOLDOUT_80_20"]){
   for(const c of [0,2,3,4,5])for(const p of POLICIES){
    const selected=d.filter(x=>x.protocol===protocol&&+x.client_count===c&&x.selection_policy===p);
    if(selected.length!==42)continue;
    const metrics={};
    for(const k of ["accuracy","balanced_accuracy","macro_f1","evaluation_rows"]){
     metrics[k]=avg(selected.map(s=>parsed(s[k])).filter(v=>v!==null));
    }
    best.push({protocol,client_count:c,policy:p,...metrics});
   }
  }
  const top=["UCI_OFFICIAL_132_28","GROUP_HOLDOUT_80_20"].map(protocol=>best.filter(x=>x.protocol===protocol).sort((a,b)=>b.balanced_accuracy-a.balanced_accuracy)[0]);
  $("hayesResults").innerHTML=top.map(x=>'<tr><td>'+esc(x.protocol)+'</td><td>'+esc((x.client_count?"C"+x.client_count:"Central")+" · "+names[x.policy])+'</td><td class="n">'+pct(x.accuracy)+'</td><td class="n">'+pct(x.balanced_accuracy)+'</td><td class="n">'+pct(x.macro_f1)+'</td><td class="n">'+x.evaluation_rows.toFixed(1)+'</td><td>42</td></tr>').join("");
  $("hayesGate").textContent="已驗證 2,520 列額外協定 × 42 Seeds。注意：官方 132/28 的 42 個 Seeds 共用相同 Test；只有聯邦式分配會隨 Seed 變化，不能當成 42 個獨立測試。";
 }catch(e){
  $("hayesGate").textContent="尚未發布通過驗證的完整新協定資料："+e.message+"；原 8,820 列 Hayes 排名暫維持研究限制，不填造結果。";
 }
}
function render(){
 if(!rows.length)return;
 const ds=$("dataset").value,metric=$("objective").value,arch=$("architect").value,pol=$("policy").value;
 const all=allStats(ds,arch,pol),list=sorted(all,metric);
 winnerUI(list,metric);barChart(list,metric);table(list,metric);frontier(all);champions();
}
async function load(){
 try{
  const r=await fetch("../data/baseline_8820.json",{cache:"no-cache"});
  if(!r.ok)throw Error("HTTP "+r.status);
  const data=await r.json();
  if(!Array.isArray(data.rows)||data.rows.length!==8820||!data.columns.includes("evaluation_rows"))throw Error("基線證據不完整");
  rows=data.rows.map(a=>Object.fromEntries(data.columns.map((k,i)=>[k,a[i]])));
  const keys=new Set();
  for(const x of rows){const k=[x.dataset,x.seed,x.split_mode,x.client_count,x.selection_policy].join("|");if(keys.has(k))throw Error("重複配置鍵");keys.add(k);}
  $("evidenceStatus").textContent="正式基準 PASS：8,820 列 × "+data.columns.length+" 欄；42 Seed、NONE 1,260、六策略 7,560；只使用 80/20 未見資料參與排名。";
  ["dataset","objective","architect","policy"].forEach(id=>$(id).onchange=render);
  render();externalResults();
 }catch(e){$("evidenceStatus").textContent="證據驗證失敗："+e.message+"。不展示未核對的最佳配置。";}
}
load();