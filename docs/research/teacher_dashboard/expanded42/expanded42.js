(()=>{
"use strict";
const el=id=>document.getElementById(id);
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt=(v,precision=0)=>v===null||v===undefined||v===""||!Number.isFinite(Number(v))?"—":Number(v).toLocaleString("en-US",{minimumFractionDigits:precision,maximumFractionDigits:precision});
const pct=v=>v===null||v===undefined?"—":fmt(v,2)+"%";
const pp=v=>v===null||v===undefined||!Number.isFinite(v)?"—":(v>=0?"+":"")+fmt(v,2)+" pp";
const opt=id=>el(id).value;
const scenes={CENTRALIZED:"Centralized",FED_IID:"Fed IID",FED_A05:"Fed α=0.5",FED_A01:"Fed α=0.1"};
const versions={A_ALL_RULES:"A · ALL RULES",B2_TRUE_AS_FALLBACK:"B2 · TRUE fallback"};
const groups={ALL:"全部已完成",FULL_FEATURE:"原始 Features ≤6",LIMITED_6:"原始 Features >6"};
let source=null,filtered=[],page=1,currentDetail=null;
const step=30;
const groupOf=r=>r.features>6?"LIMITED_6":"FULL_FEATURE";
const metric=(r,scenario,variant)=>r.variants[variant]?.[scenario]||null;
const complete=r=>r.status==="COMPLETE";
const summary=(group,scenario,variant)=>source.coverageConflict.summary.find(x=>x.group===group&&x.scenario===scenario&&x.variant===variant);
const bestLabel=v=>(v||"").replaceAll(";","／");
function riskMet(m,criterion){
 if(!m)return false;
 if(criterion==="HIGH_CONFLICT")return m.coverage>=80&&m.conflict>=50;
 if(criterion==="BAD_CANDIDATE")return m.coveredWrongPct>=20;
 if(criterion==="NO_MATCH")return m.noMatchPct>=50;
 return true;
}
function risk(r,criterion,scenario,variant){
 if(criterion==="ALL")return true;
 if(!complete(r))return false;
 const m=metric(r,scenario,variant);
 if(criterion==="B2_TRADEOFF"){
  const a=metric(r,scenario,"A_ALL_RULES"),b=metric(r,scenario,"B2_TRUE_AS_FALLBACK");
  return a&&b&&a.complete&&b.complete&&b.conflict<a.conflict-1e-9&&b.candidate<a.candidate-1e-9;
 }
 return riskMet(m,criterion);
}
function metricBars(m,title){
 if(!m)return '<article><h4>'+esc(title)+'</h4><p>此情境尚無可比較觀測值。</p></article>';
 const rows=[
  ["至少一條規則命中",m.coverage,""],
  ["含正確候選",m.candidate,"candidate"],
  ["命中但缺真實類別",m.coveredWrongPct,"gap"],
  ["沒有規則命中",m.noMatchPct,"none"],
  ["跨類別 Conflict",m.conflict,"conflict"]
 ];
 return '<article><h4>'+esc(title)+'</h4>'+rows.map(([name,value,type])=>
 '<div class="evidence-line"><span class="label">'+esc(name)+'</span>'+
 '<span class="track"><span class="fill '+type+'" style="width:'+Math.max(0,Math.min(100,value)).toFixed(3)+'%"></span></span>'+
 '<b>'+pct(value)+'</b></div>').join("")+
 '<small>Conflict 與其餘指標可能重疊；不可把所有橫條直接相加。'+
 (m.meanTestRows!==null?"平均 Test "+fmt(m.meanTestRows,1)+" 筆。":"")+'</small></article>';
}
function summaryBars(s,title){
 if(!s)return "<article><h4>無資料</h4></article>";
 return metricBars({
 coverage:s.coverage,candidate:s.candidate,coveredWrongPct:s.coveredWrong,
 noMatchPct:s.noMatch,conflict:s.conflict,meanTestRows:s.meanTestRows
 },title);
}
function drawGroups(){
 const full=source.groups.FULL_FEATURE,lim=source.groups.LIMITED_6;
 el("groupSummary").innerHTML=[[full,"≤6 完整特徵"],[lim,">6 受限六特徵"]].map(([g,label])=>
 "<tr><td>"+label+"</td><td>"+g.n+"</td><td>"+pct(g.summary.CENTRALIZED.accuracy)+"</td><td>"+
 pct(g.summary.FED_A01.accuracy)+"</td><td>"+pct(g.summary.FED_A01.coverage)+"</td><td>"+
 pct(g.summary.FED_A01.conflict)+"</td></tr>").join("");
 el("groupBars").innerHTML=[["Fed α=0.1 Test Coverage","coverage"],["Fed α=0.1 Conflict Rate","conflict"]].map(([title,key])=>{
 const lines=[[full,"≤6 Features",false],[lim,">6 Features",true]].map(([g,label,limited])=>{
 const val=g.summary.FED_A01[key];
 return '<div class="line"><span class="barlab">'+label+'</span><span class="bartrack"><span class="barfill'+(limited?" limited":"")+
 '" style="width:'+Math.min(100,val).toFixed(2)+'%"></span></span><span class="barval">'+pct(val)+'</span></div>';
 }).join("");
 return '<div class="barcard"><h4>'+title+'</h4>'+lines+
 '<small class="muted">原始特徵 ≤6：25 完整；原始 >6：154 完整。非因果比較。</small></div>';
 }).join("");
}
function drawAnalysis(){
 const grp=opt("analysisGroup"),variant=opt("analysisVariant"),focus=opt("analysisScenario");
 const focused=summary(grp,focus,variant),base=summary(grp,"CENTRALIZED",variant);
 if(!focused||!base)return;
 el("analysisHeadline").innerHTML='<strong>'+groups[grp]+' · '+versions[variant]+' · '+scenes[focus]+'</strong>'+
 '（n='+focused.n+'）<div>Test Coverage <b>'+pct(focused.coverage)+'</b>；Candidate Coverage <b>'+pct(focused.candidate)+
 '</b>；有規則命中但真實類別不在候選集合的比例 <b>'+pct(focused.coveredWrong)+'</b>；'+
 'No Match <b>'+pct(focused.noMatch)+'</b>；Conflict <b>'+pct(focused.conflict)+'</b>。'+
 '相對集中式的 Coverage <b>'+pp(focused.coverage-base.coverage)+'</b>、Conflict <b>'+pp(focused.conflict-base.conflict)+
 '</b>。Coverage≥80%且Conflict≥50%的資料集 <b>'+focused.coverage80Conflict50+' / '+focused.n+'</b>。</div>';
 el("analysisRows").innerHTML=source.scenarioKeys.map(sc=>{
 const s=summary(grp,sc,variant);
 return '<tr><th scope="row">'+scenes[sc]+'</th><td>'+s.n+'</td>'+
 '<td class="metric-highlight">'+pct(s.coverage)+'</td><td>'+pct(s.candidate)+'</td>'+
 '<td>'+pct(s.coveredWrong)+'</td><td>'+pct(s.noMatch)+'</td>'+
 '<td class="risk">'+pct(s.conflict)+'</td><td>'+fmt(s.rules,1)+'</td>'+
 '<td>'+s.coverage80Conflict50+' / '+s.n+'</td></tr>';
 }).join("");
 el("funnelViz").innerHTML=summaryBars(summary(grp,focus,"A_ALL_RULES"),"A · All Rules — "+scenes[focus])+
 summaryBars(summary(grp,focus,"B2_TRUE_AS_FALLBACK"),"B2 · TRUE fallback — "+scenes[focus]);
 el("variantTradeoff").innerHTML=source.scenarioKeys.map(sc=>{
 const a=summary(grp,sc,"A_ALL_RULES"),b=summary(grp,sc,"B2_TRUE_AS_FALLBACK");
 const cols=[b.coverage-a.coverage,b.candidate-a.candidate,b.conflict-a.conflict,
 b.coveredWrong-a.coveredWrong,b.accuracy-a.accuracy,b.ba-a.ba];
 return "<tr><th scope='row'>"+scenes[sc]+"</th>"+cols.map(x=>"<td>"+pp(x)+"</td>").join("")+"</tr>";
 }).join("");
 drawSubgroups();
 drawRiskExamples();
}
function stratum(r,dimension){
 if(dimension==="ROW_SIZE"){
  const v=r.usedRows;
  return v<500?"<500 Rows":v<5000?"500–4,999 Rows":v<50000?"5,000–49,999 Rows":"≥50,000 Rows";
 }
 if(dimension==="CLASS_COUNT")return r.classes===2?"2 類":r.classes<=5?"3–5 類":"≥6 類";
 if(dimension==="FEATURE_TYPE")return r.type||"未分類";
 if(dimension==="COHORT")return r.cohort==="OML51"?"OpenML":r.cohort;
 return "其他";
}
function drawSubgroups(){
 const grp=opt("analysisGroup"),sc=opt("analysisScenario"),vr=opt("analysisVariant");
 const dimension=opt("subgroupDimension");
 const eligible=source.rows.filter(r=>complete(r)&&(grp==="ALL"||groupOf(r)===grp));
 const dictionary=new Map();
 for(const r of eligible){
  const key=stratum(r,dimension);
  if(!dictionary.has(key))dictionary.set(key,[]);
  dictionary.get(key).push(metric(r,sc,vr));
 }
 el("subgroupDescription").textContent="已選 "+groups[grp]+"、"+scenes[sc]+"、"+versions[vr]+
 "；分層維度："+{ROW_SIZE:"實際使用 Rows",CLASS_COUNT:"決策類別數",FEATURE_TYPE:"資料型態",COHORT:"來源群組"}[dimension]+
 "。分母為 42 Seeds 全完成的 "+eligible.length+" 個資料集；不是逐筆測試樣本數。";
 const values=[...dictionary.entries()];
 if(dimension==="ROW_SIZE")values.sort((a,b)=>["<500 Rows","500–4,999 Rows","5,000–49,999 Rows","≥50,000 Rows"].indexOf(a[0])-
 ["<500 Rows","500–4,999 Rows","5,000–49,999 Rows","≥50,000 Rows"].indexOf(b[0]));
 else if(dimension==="CLASS_COUNT")values.sort((a,b)=>["2 類","3–5 類","≥6 類"].indexOf(a[0])-["2 類","3–5 類","≥6 類"].indexOf(b[0]));
 else values.sort((a,b)=>a[0].localeCompare(b[0],"zh-Hant"));
 el("subgroupRows").innerHTML=values.map(([name,arr])=>{
  const avg=k=>arr.reduce((t,m)=>t+m[k],0)/arr.length;
  const high=arr.filter(m=>m.coverage>=80&&m.conflict>=50).length;
  return "<tr><td><strong>"+esc(name)+"</strong>"+(arr.length<5?"<small class='risk'> · 小樣本</small>":"")+"</td>"+
  "<td>"+arr.length+"</td><td>"+pct(avg("coverage"))+"</td><td>"+pct(avg("candidate"))+
  "</td><td>"+pct(avg("coveredWrongPct"))+"</td><td>"+pct(avg("noMatchPct"))+
  "</td><td>"+pct(avg("conflict"))+"</td><td>"+high+" / "+arr.length+"</td></tr>";
 }).join("")||"<tr><td colspan='8'>此分組沒有完整實驗結果。</td></tr>";
}
function drawRiskExamples(){
 const grp=opt("analysisGroup"),variant=opt("analysisVariant"),sc=opt("analysisScenario");
 const eligible=source.rows.filter(r=>complete(r)&&(grp==="ALL"||groupOf(r)===grp));
 const allRisk=eligible.filter(r=>{
 const m=metric(r,sc,variant);
 return m&&(m.coverage>=80&&m.conflict>=50||m.coveredWrongPct>=20||m.noMatchPct>=50);
 });
 allRisk.sort((a,b)=>{
 const ma=metric(a,sc,variant),mb=metric(b,sc,variant);
 return (mb.coveredWrongPct-ma.coveredWrongPct)||(mb.conflict-ma.conflict)||a.name.localeCompare(b.name);
 });
 el("riskCount").textContent="在 "+groups[grp]+" 的 "+eligible.length+" 份完整資料中，"+
 allRisk.length+" 份至少觸發一項描述性風險條件。展示風險較高前 12 筆；切換分布／規則版本會同步重算。";
 el("riskExamples").innerHTML=allRisk.slice(0,12).map(r=>{
 const m=metric(r,sc,variant),a=metric(r,sc,"A_ALL_RULES"),b=metric(r,sc,"B2_TRUE_AS_FALLBACK");
 return "<tr><td><b>"+esc(r.name)+"</b><small>"+esc(r.id)+"</small></td>"+
 "<td>"+r.features+" → "+r.usedFeatures+"</td>"+
 "<td>"+pct(m.coverage)+"</td><td>"+pct(m.candidate)+"</td>"+
 "<td>"+pct(m.coveredWrongPct)+"</td><td>"+pct(m.noMatchPct)+"</td>"+
 "<td>"+pct(m.conflict)+"</td><td>"+pp(b.conflict-a.conflict)+"</td>"+
 '<td><button type="button" data-detail="'+esc(r.id)+'">檢視四情境</button></td></tr>';
 }).join("")||"<tr><td colspan='9'>此範圍未發現符合指定門檻的觀測資料。</td></tr>";
 bindDetails("riskExamples");
}
function filter(){
 const query=opt("search").toLocaleLowerCase().trim(),g=opt("featureGroup"),co=opt("cohort");
 const status=opt("completion"),sc=opt("scenario"),v=opt("variant"),criterion=opt("riskFilter");
 filtered=source.rows.filter(r=>(g==="ALL"||groupOf(r)===(g==="FULL"?"FULL_FEATURE":"LIMITED_6"))&&
 (co==="ALL"||r.cohort===co)&&(status==="ALL"||(status==="COMPLETE"?complete(r):!complete(r)))&&
 (!query||[r.id,r.name,r.cohort,r.type,...r.chosen].join(" ").toLocaleLowerCase().includes(query))&&
 risk(r,criterion,sc,v));
 const order=opt("sortBy");
 if(order!=="NAME"){
 const key={CONFLICT_DESC:"conflict",GAP_DESC:"coveredWrongPct",NO_MATCH_DESC:"noMatchPct",COVERAGE_DESC:"coverage"}[order];
 filtered.sort((a,b)=>{
 const av=metric(a,sc,v)?.[key],bv=metric(b,sc,v)?.[key];
 return (bv??-Infinity)-(av??-Infinity)||a.name.localeCompare(b.name);
 });
 }
 page=1;render();
}
function render(){
 const sc=opt("scenario"),variant=opt("variant"),pages=Math.max(1,Math.ceil(filtered.length/step));
 page=Math.max(1,Math.min(pages,page));
 const list=filtered.slice((page-1)*step,page*step);
 el("showing").textContent="符合條件 "+filtered.length+"／188 筆資料集；第 "+page+"／"+pages+
 " 頁。比例為該資料集逐 Seed 平均；不足 42 Seeds 的資料僅供觀察，不納入完整組的統計。";
 el("datasetRows").innerHTML=list.map(r=>{
 const m=metric(r,sc,variant),full=complete(r),grp=groupOf(r),fstr=r.features+" → "+r.usedFeatures;
 return '<tr><td><b>'+esc(r.name)+'</b><span class="id">'+esc(r.id)+'</span></td>'+
 '<td>'+esc(r.cohort==="OML51"?"OpenML":r.cohort)+'</td>'+
 '<td>'+fmt(r.rows)+' / '+fmt(r.usedRows)+'</td>'+
 '<td><span class="tag '+(grp==="LIMITED_6"?"limited":"")+'">'+esc(fstr)+'</span>'+
 '<small>'+(grp==="LIMITED_6"?"受限特徵基準":"保留原始候選特徵")+'</small></td>'+
 '<td>'+fmt(r.classes)+'</td>'+
 '<td><span class="status '+(full?"done":"")+'">'+(full?"完成":"缺漏")+'</span>'+
 '<small>'+r.models+' / 168</small></td>'+
 '<td><b class="num">'+pct(m?.accuracy)+'</b><small>'+(m?m.seeds+" / 42 Seeds":"未取得結果")+'</small></td>'+
 '<td><b>'+pct(m?.coverage)+'</b><small>'+(m?"命中 "+fmt(m.meanMatchedRows,1)+" / "+fmt(m.meanTestRows,1):"")+'</small></td>'+
 '<td>'+pct(m?.candidate)+'</td><td>'+pct(m?.coveredWrongPct)+'</td>'+
 '<td>'+pct(m?.noMatchPct)+'</td><td class="risk">'+pct(m?.conflict)+'</td>'+
 '<td><button type="button" data-detail="'+esc(r.id)+'">完整明細</button></td></tr>';
 }).join("")||'<tr><td colspan="13">沒有符合條件的觀測值；可取消風險篩選或切換其他情境。</td></tr>';
 el("pageInfo").textContent=page+" / "+pages;
 el("prev").disabled=page<=1;el("next").disabled=page>=pages;
 bindDetails("datasetRows");
}
function bindDetails(id){
 for(const b of el(id).querySelectorAll("button[data-detail]")){
 b.addEventListener("click",()=>detail(b.dataset.detail,true));
 }
}
function detail(id,scroll=true){
 const r=source.rows.find(x=>x.id===id);if(!r)return;currentDetail=r.id;
 const v=opt("variant"),scCurrent=opt("scenario"),selected=metric(r,scCurrent,v);
 el("detailTitle").textContent=r.name+" · "+r.id;
 const md=[
 ["來源群組",r.cohort],["原始 / 使用 Rows",fmt(r.rows)+" / "+fmt(r.usedRows)],
 ["原始 / 使用 Features",fmt(r.features)+" / "+fmt(r.usedFeatures)],["實驗類別數",fmt(r.classes)],
 ["42 Seeds 完成度",fmt(r.models)+" / 168；"+(complete(r)?"COMPLETE":"PARTIAL / MISSING")],
 ["特徵選取方法",r.selection.replaceAll("_"," ")],
 ["觀測特徵型態",r.type],["少數類別比例",r.minority===null?"未提供":pct(100*r.minority)]
 ];
 el("detailMeta").innerHTML='<div class="detail-grid">'+md.map(([k,val])=>
 '<div><b>'+esc(k)+'</b><span>'+esc(val)+'</span></div>').join("")+'</div>'+
 '<p class="selection"><b>實際選用原始特徵欄位：</b>'+esc(r.chosen.join("、")||"沒有公開名稱")+'</p>'+
 '<p class="muted small">原始目標標籤值需逐來源核實，現階段只列出類別數。三個 Clients 使用相同的已選欄位與 Target，不是平均分配 Features。</p>';
 el("detailFunnel").innerHTML=metricBars(selected,versions[v]+" · "+scenes[scCurrent])+
 metricBars(metric(r,scCurrent,v==="A_ALL_RULES"?"B2_TRUE_AS_FALLBACK":"A_ALL_RULES"),"對照版本 · "+scenes[scCurrent]);
 el("detailResults").innerHTML=source.scenarioKeys.map(sc=>{
 const m=metric(r,sc,v);
 return '<tr><th scope="row">'+scenes[sc]+'</th>'+
 (m?'<td>'+(m.complete?"42 / 42":fmt(m.seeds)+" / 42（部分）")+'</td>'+
 '<td>'+pct(m.accuracy)+'</td><td>'+pct(m.ba)+'</td>'+
 '<td>'+pct(m.coverage)+'</td><td>'+pct(m.candidate)+'</td>'+
 '<td>'+pct(m.coveredWrongPct)+'</td><td>'+pct(m.noMatchPct)+'</td>'+
 '<td>'+pct(m.conflict)+'</td><td>'+fmt(m.rules,1)+'</td><td>'+esc(bestLabel(m.accuracyMethod))+'</td>':
 '<td colspan="10">此情境尚無可比結果。</td>')+'</tr>';
 }).join("");
 el("detailAll").innerHTML=source.scenarioKeys.flatMap(sc=>source.variantKeys.map(vr=>{
 const m=metric(r,sc,vr);
 return '<tr><th scope="row">'+scenes[sc]+' / '+versions[vr]+'</th>'+
 (m?'<td>'+(m.complete?"42 / 42":fmt(m.seeds)+" / 42（部分）")+'</td>'+
 '<td>'+fmt(m.meanTestRows,1)+'</td>'+
 '<td>'+fmt(m.meanMatchedRows,1)+'</td>'+
 '<td>'+fmt(m.meanNoMatchRows,1)+'</td>'+
 '<td>'+fmt(m.meanTrueCandidateRows,1)+'</td>'+
 '<td>'+pct(m.coverage)+'</td><td>'+pct(m.candidate)+'</td>'+
 '<td>'+pct(m.noMatchPct)+'</td><td>'+pct(m.conflict)+'</td>'+
 '<td>'+pct(m.coveredWrongPct)+'</td><td>'+fmt(m.rules,1)+'</td>':
 '<td colspan="11">尚無可比較的平均數。</td>')+'</tr>';
 })).join("");
 const a=metric(r,scCurrent,"A_ALL_RULES"),b=metric(r,scCurrent,"B2_TRUE_AS_FALLBACK");
 el("detailDelta").innerHTML=a&&b&&a.complete&&b.complete?
 '<strong>同資料集・同 '+scenes[scCurrent]+'・42 Seeds：</strong>B2 相較 A，Test Coverage '+pp(b.coverage-a.coverage)+
 '；Candidate Coverage '+pp(b.candidate-a.candidate)+'；Conflict '+pp(b.conflict-a.conflict)+
 '；正確類別缺席於候選的命中缺口 '+pp(b.coveredWrongPct-a.coveredWrongPct)+
 '；事後最佳 Accuracy '+pp(b.accuracy-a.accuracy)+'；事後最佳 Balanced Accuracy '+pp(b.ba-a.ba)+
 '。<br><small>Δ 為兩個版本的資料集層級平均差，這裡不宣稱 Test-selected winner 可部署。</small>':
 'A／B2 至少一個版本尚未完成 42 個 Seeds；不使用不一致的部分實驗作為正式配對差異。';
 el("detailLinks").innerHTML='<a target="_blank" rel="noopener" href="'+esc(r.source)+'">原始資料來源</a>'+
 '<a download href="./coverage_conflict_188.csv">下載全資料集可追溯指標</a><a href="#inventory">返回資料集清單</a>';
 el("detail").hidden=false;
 if(scroll)el("detail").scrollIntoView({behavior:"smooth",block:"start"});
}
function init(data){
 if(data.rows?.length!==188||data.meta?.completeDatasets!==179||data.meta?.nOriginalLE6!==26||
 data.coverageConflict?.summary?.length!==24||data.rows.some(x=>x.usedFeatures>6))throw Error("研究快照欄位／筆數未通過驗證");
 source=data;
 el("loadStatus").textContent="驗證完成 · 凍結快照 "+data.meta.snapshot_local+" · "+
 data.meta.completeDatasets+"/"+data.meta.expectedDatasets+" 完整資料集";
 el("progressText").textContent="已完成模型 "+fmt(data.meta.completeModels)+" / "+fmt(data.meta.expectedModels)+
 "（"+fmt(100*data.meta.completeModels/data.meta.expectedModels,1)+"%）；另有 9 個資料集未完整。";
 drawGroups();drawAnalysis();filter();
 for(const id of ["search","featureGroup","cohort","completion","scenario","variant","riskFilter","sortBy"]){
 const input=el(id);
 input.addEventListener(id==="search"?"input":"change",()=>{
  filter();
  if((id==="scenario"||id==="variant")&&currentDetail)detail(currentDetail,false);
 });
 }
 for(const id of ["analysisGroup","analysisVariant","analysisScenario","subgroupDimension"]){
 el(id).addEventListener("change",drawAnalysis);
 }
 for(const b of document.querySelectorAll("[data-filter-group]")){
 b.addEventListener("click",()=>{el("featureGroup").value=b.dataset.filterGroup;filter();
 el("inventory").scrollIntoView({behavior:"smooth",block:"start"});});
 }
 el("prev").addEventListener("click",()=>{page--;render();});
 el("next").addEventListener("click",()=>{page++;render();});
}
fetch("./data.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("HTTP "+r.status);return r.json()})
.then(init).catch(e=>{
 el("loadStatus").textContent="載入或來源驗證失敗："+e.message+"。可使用下方 CSV 核對原始資料。";
 el("datasetRows").innerHTML='<tr><td colspan="13">請檢查網路與原始檔案連結。</td></tr>';
});
})();