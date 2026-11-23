(()=>{"use strict";
const el=id=>document.getElementById(id),esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let source=null,filtered=[],page=1;const step=30;
const scenes={CENTRALIZED:"Centralized",FED_IID:"Fed IID",FED_A05:"Fed α=0.5",FED_A01:"Fed α=0.1"};
const variants={A_ALL_RULES:"A · All Rules",B2_TRUE_AS_FALLBACK:"B2 · TRUE fallback"};
const n=(v,d=0)=>v==null||!Number.isFinite(Number(v))?"—":Number(v).toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d});
const pct=v=>v==null?"—":n(v,2)+"%";
const opt=id=>el(id).value;
function desc(r){return r.features>6?"LIMITED":"FULL";}
function drawGroups(){
 const gs=source.groups,full=gs.FULL_FEATURE,lim=gs.LIMITED_6;
 el("groupSummary").innerHTML=[[full,"≤6 完整特徵"],[lim,">6 受限六特徵"]].map(([g,label])=>"<tr><td>"+label+"</td><td>"+g.n+"</td><td>"+pct(g.summary.CENTRALIZED.accuracy)+"</td><td>"+pct(g.summary.FED_A01.accuracy)+"</td><td>"+pct(g.summary.FED_A01.coverage)+"</td><td>"+pct(g.summary.FED_A01.conflict)+"</td></tr>").join("");
 const measures=[["Fed α=0.1 Test Coverage","coverage"],["Fed α=0.1 Conflict Rate","conflict"]];
 el("groupBars").innerHTML=measures.map(([title,key])=>{
  const mx=Math.max(full.summary.FED_A01[key],lim.summary.FED_A01[key],100);
  const lines=[[full,"≤6 Features",false],[lim,">6 Features",true]].map(([g,label,limited])=>{
   const val=g.summary.FED_A01[key];
   return '<div class="line"><span class="barlab">'+label+'</span><span class="bartrack"><span class="barfill'+(limited?" limited":"")+'" style="width:'+Math.min(100,100*val/mx).toFixed(2)+'%"></span></span><span class="barval">'+pct(val)+'</span></div>';
  }).join("");
  return '<div class="barcard"><h4>'+title+'</h4>'+lines+'<small class="muted">179 完整資料集；分組等權平均，非因果比較</small></div>';
 }).join("");
}
function filter(){
 const text=opt("search").toLocaleLowerCase().trim(),group=opt("featureGroup"),co=opt("cohort"),state=opt("completion");
 filtered=source.rows.filter(r=>(group==="ALL"||desc(r)===group)&&(co==="ALL"||r.cohort===co)
  &&(state==="ALL"||(state==="COMPLETE"?r.status==="COMPLETE":r.status!=="COMPLETE"))
  &&(!text||[r.id,r.name,r.cohort,r.type,...r.chosen].join(" ").toLocaleLowerCase().includes(text)));
 page=1;render();
}
function render(){
 const sc=opt("scenario"),v=opt("variant");const totalPages=Math.max(1,Math.ceil(filtered.length/step));page=Math.max(1,Math.min(page,totalPages));
 const list=filtered.slice((page-1)*step,page*step);
 el("showing").textContent="目前顯示 "+filtered.length+"／188 個資料集；第 "+page+"／"+totalPages+" 頁。完整資料以來源等權統計，部分實驗不填成完整數值。";
 el("datasetRows").innerHTML=list.length?list.map(r=>{
 const met=r.variants[v][sc],group=desc(r),src=r.cohort==="OML51"?"OpenML":r.cohort,complete=r.status==="COMPLETE",s=complete?"完成":"未完成";
 const fLabel=r.features+" → "+r.usedFeatures;
 const acc=met?'<b class="num">'+pct(met.accuracy)+'</b><small>'+(met.complete?"42 Seeds":"僅 "+met.seeds+" Seeds")+'</small>':'—';
 return '<tr><td><b>'+esc(r.name)+'</b><span class="id">'+esc(r.id)+'</span></td><td>'+esc(src)+'</td><td>'+n(r.rows)+' / '+n(r.usedRows)+'</td>'+
 '<td><span class="tag '+(group==="LIMITED"?"limited":"")+'">'+esc(fLabel)+'</span><small>'+(group==="LIMITED"?"限制六特徵":"保留全部原始特徵")+'</small></td>'+
 '<td>'+n(r.classes)+'</td><td><span class="status '+(complete?"done":"")+'">'+s+'</span><small>'+r.models+' / 168</small></td>'+
 '<td>'+acc+'</td><td>'+pct(met?.coverage)+'</td><td>'+pct(met?.conflict)+'</td>'+
 '<td><button type="button" data-detail="'+esc(r.id)+'">查看</button></td></tr>';
 }).join(""):'<tr><td colspan="10">目前沒有符合條件的資料集。請調整篩選。</td></tr>';
 el("pageInfo").textContent=page+"／"+totalPages;
 el("prev").disabled=page<=1;el("next").disabled=page>=totalPages;
 for(const b of el("datasetRows").querySelectorAll("[data-detail]"))b.addEventListener("click",()=>detail(b.dataset.detail));
}
function detail(id){
 const r=source.rows.find(x=>x.id===id);if(!r)return;const v=opt("variant");let selected=r.chosen.join("、");
 el("detailTitle").textContent=r.name+" · "+r.id;
 el("detailMeta").innerHTML='<div class="detail-grid">'+[
 ["來源",r.cohort],["Original / Used Rows",n(r.rows)+" / "+n(r.usedRows)],
 ["Original / Used Features",n(r.features)+" / "+n(r.usedFeatures)],["Class 數",n(r.classes)],
 ["42 Seeds 完成度",n(r.models)+" / 168 · "+(r.status==="COMPLETE"?"完整":"待補")],
 ["選欄方式",r.selection.replaceAll("_"," ")]
 ].map(([k,v])=>'<div><b>'+esc(k)+'</b><span>'+esc(v)+'</span></div>').join("")+
 '</div><p class="selection"><strong>實際選用欄位：</strong>'+esc(selected||"未登錄")+'</p>'+
 '<p class="small muted">原始標籤名稱／值未逐項核實，本頁只展示已登錄的 Class 數與測試績效。</p>';
 el("detailResults").innerHTML=source.scenarioKeys.map(sc=>{
  const x=r.variants[v][sc];
  return '<tr><td>'+scenes[sc]+'</td>'+(x?'<td>'+(x.complete?'42 / 42':x.seeds+' / 42（部分）')+'</td><td>'+pct(x.accuracy)+'</td><td>'+pct(x.ba)+'</td><td>'+pct(x.coverage)+'</td><td>'+pct(x.candidate)+'</td><td>'+pct(x.conflict)+'</td><td>'+n(x.rules,1)+'</td><td>'+esc(x.accuracyMethod.replaceAll(";"," / "))+'</td>':'<td colspan="8">尚無此情境的結果</td>')+'</tr>';
 }).join("");
 el("detailLinks").innerHTML='<a target="_blank" rel="noopener" href="'+esc(r.source)+'">原始資料來源</a><a href="#inventory">回到篩選表格</a>';
 el("detail").hidden=false;el("detail").scrollIntoView({behavior:"smooth",block:"start"});
}
function init(j){
 if(j.rows?.length!==188||j.meta?.completeDatasets!==179||j.meta?.nOriginalLE6!==26)throw Error("研究快照驗證失敗");
 source=j;el("loadStatus").textContent="驗證完成 · 凍結來源 "+j.meta.snapshot_local+" · "+j.meta.completeDatasets+"/"+j.meta.expectedDatasets+" 完整資料集";
 el("progressText").textContent="模型 "+n(j.meta.completeModels)+" / "+n(j.meta.expectedModels)+" 成功（"+n(100*j.meta.completeModels/j.meta.expectedModels,1)+"%）；固定期中快照；9 個來源尚未完成。";
 drawGroups();filter();for(const id of ["search","featureGroup","cohort","completion","scenario","variant"]){
  el(id).addEventListener(id==="search"?"input":"change",()=>{if(id==="scenario"||id==="variant"){render();if(!el("detail").hidden){const old=el("detailTitle").textContent.split(" · ").slice(-1)[0];if(source.rows.find(x=>x.id===old))detail(old);}}else filter();});
 }
 for(const b of document.querySelectorAll("[data-filter-group]"))b.addEventListener("click",()=>{
  el("featureGroup").value=b.dataset.filterGroup;filter();el("inventory").scrollIntoView({behavior:"smooth"});
 });
 el("prev").addEventListener("click",()=>{page--;render();});el("next").addEventListener("click",()=>{page++;render();});
}
fetch("./data.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("HTTP "+r.status);return r.json()}).then(init).catch(e=>{
 el("loadStatus").textContent="無法驗證資料："+e.message+"；請改用下方 GitHub 原始表格。";
 el("datasetRows").innerHTML='<tr><td colspan="10">資料載入失敗，請檢查原始表格連結。</td></tr>';
});
})();