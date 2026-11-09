/* Deep evidence: 8,820 fully executed records, no synthetic score filling. */
(()=>{"use strict";
const $=id=>document.getElementById(id);
const S="http://www.w3.org/2000/svg",limit=75;
const metricKeys=["dataset","seed","split_mode","system","client_count","selection_policy","rule_count","coverage","conflict_case_rate","true_in_candidate_rate","accuracy","balanced_accuracy","macro_f1"];
let data=[],subset=[],page=0,valid=false;
const pct=v=>v==null||!Number.isFinite(+v)?"—":(v*100).toFixed(2)+"%";
const num=v=>v==null||!Number.isFinite(+v)?"—":Number(v).toLocaleString("zh-TW",{maximumFractionDigits:2});
const percentKey=k=>k!=="rule_count"&&k!=="seed"&&k!=="client_count";
const value=(r,k)=>r[k]==null?null:Number(r[k]);
const avg=(rows,key)=>{const arr=rows.map(r=>value(r,key)).filter(v=>v!==null&&Number.isFinite(v));return arr.length?arr.reduce((a,b)=>a+b,0)/arr.length:null;};
function node(tag,attributes={},content){const n=document.createElementNS(S,tag);Object.entries(attributes).forEach(([k,v])=>n.setAttribute(k,String(v)));if(content!==undefined)n.textContent=content;return n;}
function text(svg,x,y,t,more={}){svg.append(node("text",{x,y,"font-size":11,fill:"#5f7585",...more},t));}
function curve(svg,vals,{positiveOnly=false,signed=false}={}){
 svg.replaceChildren();const nums=vals.map(v=>v.value).filter(v=>v!==null);
 if(!nums.length){text(svg,40,62,"這個設定沒有定義數值（例如 NONE 的分類準確率）",{fill:"#b85b54","font-size":17});return;}
 const lo=signed?Math.min(0,...nums)*1.1:positiveOnly?0:Math.max(0,Math.min(...nums)*.8);
 const hi=Math.max(positiveOnly?1:0,...nums)*1.12||(positiveOnly?1:.1);
 const x=n=>58+(n-1)*(1002/41),y=v=>237-(v-lo)/(hi-lo||1)*197;
 for(let i=0;i<5;i++){const v=lo+(hi-lo)*i/4, yy=y(v);svg.append(node("line",{x1:58,y1:yy,x2:1076,y2:yy,stroke:"#e4ebed"}));text(svg,52,yy+4,positiveOnly?(v*100).toFixed(0)+"%":(v*100).toFixed(1)+"pp",{"text-anchor":"end"});}
 const poly=vals.filter(v=>v.value!==null).map(v=>x(v.seed)+","+y(v.value)).join(" ");
 svg.append(node("polyline",{points:poly,fill:"none",stroke:"#13867d","stroke-width":2.5}));
 vals.forEach(v=>{if(v.value===null)return;const c=node("circle",{cx:x(v.seed),cy:y(v.value),r:3.5,fill:v.value<0?"#c56a5b":"#13877c"});c.append(node("title",{},"Seed "+v.seed+": "+(positiveOnly?pct(v.value):((v.value*100).toFixed(2)+" pp"))));svg.append(c);});
 for(const i of [1,7,14,21,28,35,42])text(svg,x(i),265,String(i),{"text-anchor":"middle"});
}
function escaped(x){return String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function sel(){return {ds:$("ds").value,seed:$("seed").value,split:$("split").value,system:$("system").value,clients:$("clients").value,policy:$("policy").value,metric:$("metric").value};}
function renderPage(){
 const part=subset.slice(page*limit,(page+1)*limit);
 const body=$("dataRows");body.innerHTML=part.map(r=>{
   const cells=[r.dataset,r.seed,r.split_mode,r.system,r.client_count,r.selection_policy,r.rule_count];
   const html=cells.map((v,i)=>"<td"+(i===1||i===4||i===6?" class='n'":"")+">"+escaped(v)+"</td>").join("");
   return "<tr>"+html+[r.coverage,r.conflict_case_rate,r.true_in_candidate_rate,r.accuracy,r.balanced_accuracy,r.macro_f1].map(v=>"<td class='n'>"+pct(v)+"</td>").join("")+"</tr>";
 }).join("");
 $("pageInfo").textContent="第 "+(page+1)+" / "+Math.max(1,Math.ceil(subset.length/limit))+" 頁，顯示 "+part.length+" 列（全部 "+subset.length+" 列）";
 $("prev").disabled=page===0;$("next").disabled=(page+1)*limit>=subset.length;
}
function apply(){
 if(!valid)return;const q=sel();page=0;
 subset=data.filter(r=>(q.ds==="ALL"||r.dataset===q.ds)&&(q.seed==="ALL"||Number(r.seed)===Number(q.seed))&&
 (q.split==="ALL"||r.split_mode===q.split)&&(q.system==="ALL"||r.system===q.system)&&
 (q.clients==="ALL"||Number(r.client_count)===Number(q.clients))&&(q.policy==="ALL"||r.selection_policy===q.policy));
 $("shownRows").textContent=num(subset.length);renderPage();
 $("selectionInfo").textContent="指標 "+q.metric+"；符合條件 "+subset.length+" 列。當策略選擇「全部」時，曲線是多種策略的描述性平均，不代表其中任何單一策略。";
 const result=Array.from({length:42},(_,i)=>{
  const seed=i+1,one=subset.filter(r=>Number(r.seed)===seed),metric=avg(one,q.metric);
  return {seed,value:metric};
 });
 const nums=result.map(r=>r.value).filter(v=>v!==null);
 const graph=$("trend");graph.replaceChildren();
 if(!nums.length){text(graph,38,67,"目前篩選下此指標未定義",{fill:"#b15b59","font-size":18});return;}
 const large=q.metric==="rule_count";const min=large?Math.max(0,Math.min(...nums)*.85):0,max=large?Math.max(1,Math.max(...nums)*1.05):1;
 const x=i=>55+(i-1)*(1000/41),y=v=>240-(v-min)/(max-min||1)*196;
 for(let i=0;i<5;i++){const v=min+(max-min)*i/4,yy=y(v);graph.append(node("line",{x1:55,y1:yy,x2:1080,y2:yy,stroke:"#e4eef0"}));text(graph,47,yy+4,large?v.toFixed(0):(v*100).toFixed(0)+"%",{"text-anchor":"end"});}
 graph.append(node("polyline",{points:result.filter(r=>r.value!==null).map(r=>x(r.seed)+","+y(r.value)).join(" "),fill:"none",stroke:"#167d78","stroke-width":2.5}));
 result.forEach(r=>{if(r.value===null)return;const c=node("circle",{cx:x(r.seed),cy:y(r.value),r:3.2,fill:"#147a72"});c.append(node("title",{},"Seed "+r.seed+" = "+(large?num(r.value):pct(r.value))));graph.append(c);});
 for(const i of [1,7,14,21,28,35,42])text(graph,x(i),270,String(i),{"text-anchor":"middle"});
}
function paired(mode,ds){
 const rows=data.filter(r=>r.split_mode==="HOLDOUT_80_20"&&r.system==="FEDERATED"&&(ds==="ALL"||r.dataset===ds));
 const f=(all,seed,policy,metric,client,split="HOLDOUT_80_20")=>avg(all.filter(r=>r.seed===seed&&r.selection_policy===policy&&r.split_mode===split&&(client==="ALL"||r.client_count===client)),metric);
 return Array.from({length:42},(_,i)=>{
  const seed=i+1;let a=null,b=null,tag="";
  if(mode.startsWith("GS_STD_")){
   const metric=mode.endsWith("BA")?"balanced_accuracy":mode.endsWith("ACC")?"accuracy":"macro_f1";
   a=f(rows,seed,"STANDARD_VOTING",metric,"ALL");b=f(rows,seed,"GLOBAL_STRENGTH",metric,"ALL");tag=metric;
  }else if(mode.startsWith("C5_C2_")){
   const metric=mode.endsWith("CONFLICT")?"conflict_case_rate":"coverage";
   a=f(rows,seed,"NONE",metric,2);b=f(rows,seed,"NONE",metric,5);tag=metric;
  }else{
   const central=data.filter(r=>r.system==="CENTRALIZED"&&r.selection_policy==="NONE"&&(ds==="ALL"||r.dataset===ds));
   a=f(central,seed,"NONE","rule_count",0,"FULL_DATA");b=f(central,seed,"NONE","rule_count",0,"HOLDOUT_80_20");tag="rule_count";
  }
  return {seed,a,b,value:a===null||b===null?null:b-a,tag};
 });
}
function showPairs(){
 if(!valid)return;const mode=$("comparison").value,ds=$("compareDs").value;
 const result=paired(mode,ds),values=result.map(r=>r.value).filter(v=>v!==null);
 const count=mode==="HOLDOUT_FULL_RULE";
 const meanDelta=values.length?values.reduce((a,b)=>a+b,0)/values.length:null;
 $("delta").textContent=meanDelta==null?"—":count?num(meanDelta)+" 條":(meanDelta*100).toFixed(2)+" pp";
 $("wins").textContent=values.filter(x=>x>0).length+" / "+values.length;
 $("compareRows").innerHTML=result.map(r=>"<tr><td>"+r.seed+"</td><td class='n'>"+(count?num(r.a):pct(r.a))+"</td><td class='n'>"+(count?num(r.b):pct(r.b))+"</td><td class='n'>"+(r.value==null?"—":count?num(r.value):(r.value*100).toFixed(2)+" pp")+"</td></tr>").join("");
 const svg=$("compareChart");if(count){ // make plot unit-aware without labeling counts as percentages
   svg.replaceChildren();
   const nums=result.map(r=>r.value).filter(v=>v!==null);if(!nums.length)return;
   const lo=Math.min(0,...nums)*1.1,hi=Math.max(0,...nums)*1.1||1,x=s=>56+(s-1)*1000/41,y=v=>230-(v-lo)/(hi-lo||1)*186;
   for(let i=0;i<5;i++){const z=lo+(hi-lo)*i/4,yy=y(z);svg.append(node("line",{x1:55,y1:yy,x2:1080,y2:yy,stroke:"#e3eaec"}));text(svg,50,yy+4,z.toFixed(0),{"text-anchor":"end"});}
   svg.append(node("polyline",{points:result.filter(r=>r.value!=null).map(r=>x(r.seed)+","+y(r.value)).join(" "),fill:"none",stroke:"#14867e","stroke-width":2.5}));
   for(let i of [1,7,14,21,28,35,42])text(svg,x(i),265,String(i),{"text-anchor":"middle"});
 }else curve(svg,result,{signed:true}); 
}
function downloadSelected(){
 if(!subset.length)return;
 const values=[metricKeys.join(","),...subset.map(r=>metricKeys.map(k=>'"'+String(r[k]??"").replace(/"/g,'""')+'"').join(","))];
 const link=document.createElement("a"),url=URL.createObjectURL(new Blob(["\ufeff"+values.join("\n")],{type:"text/csv;charset=utf-8"}));
 link.href=url;link.download="LEM2_8820_filtered_evidence.csv";link.click();setTimeout(()=>URL.revokeObjectURL(url),500);
}
function verify(rows){
 if(rows.length!==8820)throw Error("預期 8,820 列，實際 "+rows.length);
 const counts=new Map(),none=new Map(),keys=new Set();
 for(const r of rows){const k=[r.dataset,r.seed,r.split_mode,r.system,r.client_count,r.selection_policy].join("|");
 if(keys.has(k))throw Error("重複鍵 "+k);keys.add(k);
 counts.set(Number(r.seed),(counts.get(Number(r.seed))||0)+1);
 if(r.selection_policy==="NONE")none.set(Number(r.seed),(none.get(Number(r.seed))||0)+1);}
 for(let seed=1;seed<=42;seed++)if(counts.get(seed)!==210||none.get(seed)!==30)throw Error("Seed "+seed+" 缺少完整 210/30 列");
 return true;
}
async function init(){
 try{
  const res=await fetch("../data/baseline_8820.json",{cache:"no-cache"});if(!res.ok)throw Error("HTTP "+res.status);
  const j=await res.json();
  if(!j.columns||!j.rows)throw Error("資料檔格式無效");
  data=j.rows.map(row=>Object.fromEntries(j.columns.map((k,i)=>[k,row[i]])));
  valid=verify(data);
  $("validState").textContent="42 / 42 PASS";$("totalRows").textContent=num(data.length);
  for(let seed=1;seed<=42;seed++){const opt=document.createElement("option");opt.value=String(seed);opt.textContent="Seed "+seed;$("seed").appendChild(opt);}
  const requested=new URL(location.href).searchParams.get("seed");if(requested&&Number.isInteger(+requested)&&+requested>=1&&+requested<=42)$("seed").value=requested;
  ["ds","seed","split","system","clients","policy","metric"].forEach(k=>$(k).onchange=apply);
  $("comparison").onchange=showPairs;$("compareDs").onchange=showPairs;
  $("prev").onclick=()=>{if(page>0){page--;renderPage();}};$("next").onclick=()=>{if((page+1)*limit<subset.length){page++;renderPage();}};
  $("download").onclick=downloadSelected;
  $("reset").onclick=()=>{for(const k of ["ds","seed","split","system","clients","policy"])$(k).value="ALL";$("metric").value="conflict_case_rate";apply();};
  apply();showPairs();
 }catch(e){valid=false;$("validState").textContent="驗證失敗";$("dataRows").innerHTML="<tr><td colspan='13'>資料載入錯誤："+escaped(e.message)+"</td></tr>";}
}
init();
})();