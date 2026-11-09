/* 42 Seed professor report: chart every figure directly from frozen 8820-row baseline. */
(() => {
"use strict";
const root="data/baseline_8820.json";
const $=id=>document.getElementById(id);
const ns="http://www.w3.org/2000/svg";
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pol=["GLOBAL_STRENGTH","STANDARD_VOTING","POPULATION_GLOBAL","POPULATION_STANDARD","FIRST_MATCH","SIMPLE_VOTING"];
const pnames={"GLOBAL_STRENGTH":"GS","STANDARD_VOTING":"STD","POPULATION_GLOBAL":"PG","POPULATION_STANDARD":"PS","FIRST_MATCH":"FIRST","SIMPLE_VOTING":"SIMPLE"};
const fields=["dataset","seed","split_mode","system","client_count","selection_policy","rule_count","coverage","conflict_case_rate","true_in_candidate_rate","accuracy","balanced_accuracy","macro_f1"];
let data=[],valid=new Set(),currentSeed=42;
const colors={teal:"#14847a",blue:"#557da7",gold:"#c18a42",red:"#bf6263",muted:"#6d7f8c"};
function el(name,attrs={},text){
 const n=document.createElementNS(ns,name);
 for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));
 if(text!==undefined)n.textContent=text;
 return n;
}
function text(svg,x,y,value,extra={}){const n=el("text",{x,y,"font-size":"11",fill:"#557282",...extra},value);svg.append(n);return n;}
function clear(svg){svg.replaceChildren();}
function line(svg,x1,y1,x2,y2,stroke="#e7edf0",width=1){svg.append(el("line",{x1,y1,x2,y2,stroke,"stroke-width":width}));}
function mean(rows,key){const a=rows.map(r=>r[key]).filter(v=>v!=null&&Number.isFinite(+v)).map(Number);return a.length?a.reduce((x,y)=>x+y,0)/a.length:null;}
function pct(x){return x==null||!Number.isFinite(+x)?"—":(100*x).toFixed(2)+"%";}
function number(x){return x==null||!Number.isFinite(+x)?"—":(+x).toLocaleString("zh-TW",{maximumFractionDigits:2});}
function source(mode){return data.filter(r=>r.selection_policy==="NONE"&&r.split_mode===mode);}
function filter(rows,dataset){return dataset==="ALL"?rows:rows.filter(r=>r.dataset===dataset);}
function matchTopology(rows,id){return id===0?rows.filter(r=>r.system==="CENTRALIZED"):rows.filter(r=>r.system==="FEDERATED"&&Number(r.client_count)===id);}
function config(){return {dataset:$("datasetFilter").value,split:$("splitFilter").value,metric:$("seedMetric").value,client:Number($("topologyFilter").value)};}
function scaleAxes(svg,values,{left=54,right=585,top=34,bottom=270,min=0,max=1,percent=true}={}){
 const yy=v=>bottom-(v-min)/(max-min||1)*(bottom-top);
 for(let i=0;i<=4;i++){
  const v=min+(max-min)*i/4,y=yy(v);
  line(svg,left,y,right,y);
  text(svg,left-9,y+4,percent?(v*100).toFixed(0)+"%":v.toFixed(0),{"text-anchor":"end"});
 }
 return {left,right,top,bottom,yy};
}
function graphConflict(dataset,mode){
 const svg=$("conflictChart");clear(svg);
 const vals=[0,2,3,4,5].map(c=>mean(matchTopology(filter(source(mode),dataset),c),"conflict_case_rate"));
 const {left,right,yy}=scaleAxes(svg,vals);
 const w=(right-left)/5,positions=[];
 vals.forEach((v,i)=>{
  const x=left+10+i*w;
  const h=(v||0)*(270-34),y=270-h;
  svg.append(el("rect",{x,y,width:w-20,height:h,rx:5,fill:i===0?colors.blue:colors.teal,opacity:".89"}));
  text(svg,x+(w-20)/2,Math.max(21,y-7),pct(v),{"text-anchor":"middle","font-size":"12",fill:colors.teal});
  text(svg,x+(w-20)/2,295,i===0?"Central":"C"+(i+1),{"text-anchor":"middle"});
 });
}
function graphCoverage(dataset,mode){
 const svg=$("coverageChart");clear(svg);
 const {left,right,yy}=scaleAxes(svg,[],{});
 const ids=[0,2,3,4,5],space=(right-left)/5;
 ids.forEach((c,i)=>{
  const rows=matchTopology(filter(source(mode),dataset),c);
  const vals=[mean(rows,"coverage"),mean(rows,"true_in_candidate_rate")];
  vals.forEach((v,j)=>{
   const w=space*.26,x=left+i*space+space*.24+j*(w+5),y=yy(v||0);
   svg.append(el("rect",{x,y,width:w,height:270-y,rx:3,fill:j===0?colors.blue:colors.gold}));
   const circle=el("title",{},(c?("C"+c):"Central")+" · "+(j===0?"Coverage":"True-in-Candidate")+" "+pct(v));
   svg.lastChild.append(circle);
  });
  text(svg,left+i*space+space*.5,295,c?"C"+c:"Central",{"text-anchor":"middle"});
 });
 text(svg,340,18,"■ Coverage",{fill:colors.blue,"font-size":"13"});text(svg,444,18,"■ True-in-Candidate",{fill:colors.gold,"font-size":"13"});
}
function graphSeed(dataset,mode,client,metric){
 const svg=$("seedChart");clear(svg);
 const pol=metric==="accuracy"||metric==="balanced_accuracy"?"GLOBAL_STRENGTH":"NONE";
 const sub=filter(data.filter(r=>r.split_mode===mode&&r.selection_policy===pol),dataset);
 const items=Array.from({length:42},(_,i)=>{
  const seed=i+1;
  return {seed,value:mean(matchTopology(sub.filter(r=>Number(r.seed)===seed),client),metric)};
 });
 const raw=items.map(r=>r.value).filter(v=>v!=null);
 if(!raw.length){text(svg,50,60,"此組合的指標沒有定義");return;}
 const count=metric==="rule_count";const min=count?Math.max(0,Math.floor(Math.min(...raw)*.78)):0;const max=count?Math.ceil(Math.max(...raw)*1.08):1;
 const left=58,right=1080,top=30,bottom=240;
 const yy=v=>bottom-(v-min)/(max-min||1)*(bottom-top);
 for(let i=0;i<=4;i++){const v=min+(max-min)*i/4,y=yy(v);line(svg,left,y,right,y);text(svg,left-12,y+4,count?v.toFixed(0):(v*100).toFixed(0)+"%",{"text-anchor":"end"});}
 const xx=s=>left+(s-1)*(right-left)/41;
 const pts=items.filter(r=>r.value!=null).map(r=>xx(r.seed)+","+yy(r.value)).join(" ");
 svg.append(el("polyline",{points:pts,fill:"none",stroke:colors.teal,"stroke-width":"2.6","stroke-linecap":"round"}));
 items.forEach(r=>{if(r.value==null)return;
   const circ=el("circle",{cx:xx(r.seed),cy:yy(r.value),r:r.seed===currentSeed?6:3.4,fill:r.seed===currentSeed?colors.gold:colors.teal,tabindex:"0",role:"button","aria-label":"Seed "+r.seed});
   circ.append(el("title",{},"Seed "+r.seed+"："+(count?number(r.value):pct(r.value))));
   const go=()=>{currentSeed=r.seed;updateGrid();graphSeed(dataset,mode,client,metric);};
   circ.addEventListener("click",go);circ.addEventListener("keydown",e=>{if(e.key==="Enter")go();});
   svg.append(circ);
 });
 for(const n of [1,7,14,21,28,35,42])text(svg,xx(n),270,String(n),{"text-anchor":"middle","font-size":"12"});
 const row=items.find(r=>r.seed===currentSeed);
 $("seedChartCaption").innerHTML="選定 Seed <b>"+currentSeed+"</b>："+
  (row.value==null?"未定義":count?number(row.value):pct(row.value))+
  "；此處每個點對應相同資料／同一種切分／同一拓樸。"+
  ' <a href="./evidence/?seed='+currentSeed+'">查看 Seed '+currentSeed+' 的全部配置</a>';
}
function topologyTable(dataset,mode){
 const rows=filter(source(mode),dataset);const t=[];
 for(const c of [0,2,3,4,5]){
  const rr=matchTopology(rows,c);
  t.push("<tr><td>"+(c?"Federated C"+c:"Centralized")+"</td><td class='n'>"+
   number(mean(rr,"rule_count"))+"</td><td class='n'>"+pct(mean(rr,"coverage"))+"</td><td class='n'>"+
   pct(mean(rr,"true_in_candidate_rate"))+"</td><td class='n'>"+pct(mean(rr,"conflict_case_rate"))+"</td></tr>");
 }
 $("topologyTable").innerHTML=t.join("");
}
function graphPolicy(dataset,mode){
 const rows=filter(data.filter(r=>r.split_mode===mode&&r.system==="FEDERATED"&&r.selection_policy!=="NONE"),dataset);
 const svg=$("policyChart");clear(svg);
 const left=75,right=1100,top=40,bottom=306;const w=(right-left)/pol.length;
 const met=["accuracy","balanced_accuracy","macro_f1"],c=[colors.teal,colors.gold,colors.blue];
 for(let i=0;i<=4;i++){
  const v=i/4,y=bottom-v*(bottom-top);line(svg,left,y,right,y);
  text(svg,left-12,y+5,Math.round(v*100)+"%",{"text-anchor":"end"});
 }
 const output=[];
 pol.forEach((name,i)=>{
  const slice=rows.filter(r=>r.selection_policy===name);
  const values=met.map(m=>mean(slice,m));
  values.forEach((v,j)=>{
   const bw=30,x=left+i*w+26+j*34,y=bottom-(v||0)*(bottom-top);
   const r=el("rect",{x,y,width:bw,height:bottom-y,rx:3,fill:c[j]});
   r.append(el("title",{},name+" "+met[j]+" "+pct(v)));svg.append(r);
  });
  text(svg,left+i*w+w/2,334,pnames[name],{"text-anchor":"middle","font-size":"14",fill:"#335970"});
  const hint=name==="GLOBAL_STRENGTH"?"類別權重平衡較佳（但未普遍優於 STD）":name==="FIRST_MATCH"?"可能受 Client 規則順序影響":name.startsWith("POPULATION")?"去除重複支持≠保證提升":"依當前規則投票";
  output.push("<tr><td>"+name+"</td>"+values.map(v=>"<td class='n'>"+pct(v)+"</td>").join("")+"<td>"+hint+"</td></tr>");
 });
 $("policyTable").innerHTML=output.join("");
 text(svg,800,20,"■ Accuracy",{fill:colors.teal,"font-size":"14"});text(svg,920,20,"■ BA",{fill:colors.gold,"font-size":"14"});text(svg,998,20,"■ Macro-F1",{fill:colors.blue,"font-size":"14"});
}
function updateGrid(){
 const g=$("seedGrid");g.replaceChildren();
 for(let s=1;s<=42;s++){
  const b=document.createElement("button");
  b.textContent=String(s);b.type="button";b.className=(valid.has(s)?"good":"missing")+(s===currentSeed?" active":"");
  b.title="Seed "+s+"： "+(valid.has(s)?"210 筆通過驗證":"缺少完整證據");
  b.setAttribute("aria-pressed",String(s===currentSeed));
  b.onclick=()=>{currentSeed=s;updateGrid();const c=config();graphSeed(c.dataset,c.split,c.client,c.metric);};
  g.appendChild(b);
 }
}
function update(){
 const c=config();graphConflict(c.dataset,c.split);graphCoverage(c.dataset,c.split);
 graphSeed(c.dataset,c.split,c.client,c.metric);topologyTable(c.dataset,c.split);
 graphPolicy(c.dataset,c.split);
}
function verified(data){
 const counts=new Map(),none=new Map(),keys=new Set();
 for(const r of data){
  const k=[r.seed,r.dataset,r.split_mode,r.system,r.client_count,r.selection_policy].join("|");
  if(keys.has(k))throw Error("實驗鍵重複："+k);keys.add(k);
  const n=Number(r.seed);counts.set(n,(counts.get(n)||0)+1);
  if(r.selection_policy==="NONE")none.set(n,(none.get(n)||0)+1);
 }
 const s=new Set();for(let n=1;n<=42;n++)if(counts.get(n)===210&&none.get(n)===30)s.add(n);
 if(data.length!==8820||s.size!==42)throw Error("8,820 筆或 42 Seeds 驗證不完整");
 return s;
}
async function load(){
 try{
  const res=await fetch(root,{cache:"no-cache"});if(!res.ok)throw Error("HTTP "+res.status);
  const input=await res.json();if(!Array.isArray(input.columns)||!Array.isArray(input.rows))throw Error("證據 JSON 格式不正確");
  const output=input.rows.map(row=>Object.fromEntries(input.columns.map((k,i)=>[k,row[i]])));
  valid=verified(output);data=output;
  $("seedKpi").textContent=valid.size+" / 42";$("evidenceState").textContent="8,820 筆資料檢查 PASS";
  $("seedEvidenceStatus").textContent="42/42 Seeds 完整，逐個 Seed 210 筆（其中 30 NONE、180 六策略）；綠色由數據即時計算。";
  updateGrid();update();
 }catch(e){
  $("seedKpi").textContent="未能驗證";$("evidenceState").textContent="證據載入失敗";
  $("seedEvidenceStatus").textContent="無法讀取已凍結數據："+e.message+"。以下靜態段落仍可閱讀，但不顯示虛假的動態圖表。";
  for(const id of ["conflictChart","coverageChart","seedChart","policyChart"]){
   const svg=$(id);clear(svg);text(svg,35,60,"無法讀取實驗檔，請檢查 GitHub Pages / data/baseline_8820.json",{fill:colors.red,"font-size":"17"});
  }
 }
}
for(const id of ["datasetFilter","splitFilter","seedMetric","topologyFilter"])$(id).addEventListener("change",()=>{if(data.length)update();});
updateGrid();load();
})();