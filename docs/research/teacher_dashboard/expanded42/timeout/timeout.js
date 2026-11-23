(()=>{
"use strict";
const $=id=>document.getElementById(id),S="http://www.w3.org/2000/svg";
const esc=x=>String(x??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const num=(x,d=0)=>x==null||x===""||!Number.isFinite(Number(x))?"—":Number(x).toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d});
const flag=(text,type="")=>'<span class="evidence-flag '+type+'">'+esc(text)+'</span>';
async function readCsvGzip(path){
 const res=await fetch(path,{cache:"no-store"});if(!res.ok)throw Error(path+" "+res.status);
 const input=new Uint8Array(await res.arrayBuffer());
 let readable;
 if(input[0]===31&&input[1]===139){
  if(!window.DecompressionStream)throw Error("瀏覽器不支援 gzip DecompressionStream");
  readable=new Blob([input]).stream().pipeThrough(new DecompressionStream("gzip"));
 } else readable=new Blob([input]).stream();
 const raw=await new Response(readable).text();
 const lines=raw.trim().replace(/\r/g,"").split("\n");const keys=lines.shift().split(",");
 return lines.map(line=>Object.fromEntries(line.split(",").map((v,i)=>[keys[i],v])));
}
const asNumber=(r,k)=>r[k]===""||r[k]===undefined?null:Number(r[k]);
const svg=(parent,tag,attrs={},text)=>{const e=document.createElementNS(S,tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,String(v));if(text!==undefined)e.textContent=text;parent.appendChild(e);return e;};
const bounds={l:89,r:1033,t:55,b:505};
const proj=(v,min,max,left,right)=>left+(Math.log10(v)-min)/(max-min)*(right-left);
const coords=(r,t,lim)=>[proj(r,2,6.5,bounds.l,bounds.r),proj(t,-1,lim,bounds.b,bounds.t)];
const fmtTick=(v)=>v>=1e6?"1M":v>=1e3?num(v/1000)+"k":num(v);
function axes(g,title,ytop){
 svg(g,"text",{x:530,y:32,"text-anchor":"middle",class:"chart-title"},title);
 for(const row of [1e2,1e3,1e4,1e5,1e6]){
  const x=coords(row,1,ytop)[0];svg(g,"line",{x1:x,y1:bounds.t,x2:x,y2:bounds.b,stroke:"#e5edf0"});
  svg(g,"text",{x,y:bounds.b+23,"text-anchor":"middle",class:"axis-tick"},fmtTick(row));
 }
 const ticks=ytop===5?[1,10,100,1000,10000,100000]:[.1,1,10,100,1000,10000];
 for(const t of ticks){
  const y=coords(100,t,ytop)[1];svg(g,"line",{x1:bounds.l,y1:y,x2:bounds.r,y2:y,stroke:"#e5edf0"});
  svg(g,"text",{x:bounds.l-13,y:y+4,"text-anchor":"end",class:"axis-tick"},fmtTick(t));
 }
 const y=coords(100,2700,ytop)[1];
 svg(g,"line",{x1:bounds.l,y1:y,x2:bounds.r,y2:y,stroke:"#c64262","stroke-width":2,"stroke-dasharray":"9,7"});
 svg(g,"text",{x:bounds.l+10,y:y-9,fill:"#b84764","font-weight":750,"font-size":13},"2,700s deadline");
 svg(g,"line",{x1:bounds.l,y1:bounds.t,x2:bounds.l,y2:bounds.b,stroke:"#597481","stroke-width":1.4});
 svg(g,"line",{x1:bounds.l,y1:bounds.b,x2:bounds.r,y2:bounds.b,stroke:"#597481","stroke-width":1.4});
 svg(g,"text",{x:565,y:558,"text-anchor":"middle",class:"axis-label"},"source Rows / full Rows (log)");
 svg(g,"text",{x:23,y:280,transform:"rotate(-90 23 280)","text-anchor":"middle",class:"axis-label"},"model wall time (s, log)");
}
function markX(g,x,y,caption){
 for(const d of [-1,1])svg(g,"line",{x1:x-7,y1:y-7*d,x2:x+7,y2:y+7*d,class:"cross-mark"});
 if(caption)svg(g,"text",{x:x-10,y:y-12,fill:"#b83c57","text-anchor":x>850?"end":"start","font-size":13},caption);
}
const sourcesExample=["OML51:openml_41027","OML51:openml_42769","UCI20:covertype","OML51:openml_4541","PMLB:sleep","OML51:openml_41150","UCI20:letter"];
function scatter(rows){
 const target=$("scatterSvg");target.replaceChildren();axes(target,"Rows vs completed-model slowest observed wall time",4);
 for(const r of rows){
  const xx=asNumber(r,"original_rows"),yy=asNumber(r,"max_wall_s");
  if(!xx||!yy||xx<100)continue;
  const [x,y]=coords(xx,yy,4);
  const circle=svg(target,"circle",{cx:x,cy:y,r:4.1,fill:"#3f96bb","fill-opacity":.6,stroke:"#2d7ea9","stroke-width":.8});
  svg(circle,"title",{},r.dataset+" / Rows "+num(xx)+" / slowest completed "+num(yy,2)+" s / median rules "+num(asNumber(r,"median_rules"),1));
 }
 for(const pair of [[44819,"openml_41027"],[2215023,"openml_42732"]]){
  const[x,y]=coords(pair[0],2700,4);markX(target,x,y,pair[1]);
 }
 for(const id of ["OML51:openml_42769","UCI20:covertype","OML51:openml_4541","PMLB:sleep","UCI20:letter"]){
  const row=rows.find(r=>r.dataset===id);if(!row)continue;
  const[x,y]=coords(asNumber(row,"original_rows"),asNumber(row,"max_wall_s"),4);
  svg(target,"text",{x:x+7,y:y-10,"font-size":12,fill:"#304b5b"},id.split(":").slice(-1)[0]);
 }
 const notes={
 "OML51:openml_41027":"2 個成功模型，另有大量 TIMEOUT",
 "OML51:openml_42769":"大資料且規則少",
 "UCI20:covertype":"大資料且規則少",
 "OML51:openml_4541":"規則多且耗時顯著",
 "PMLB:sleep":"中大型資料對照",
 "OML51:openml_41150":"規則極少",
 "UCI20:letter":"規則很多但未達 TIMEOUT"
 };
 $("fastSlowCases").innerHTML=sourcesExample.map(id=>{
  const r=rows.find(x=>x.dataset===id);if(!r)return "";
  return '<tr><td>'+esc(id)+'</td><td>'+num(asNumber(r,"original_rows"))+'</td><td>'+
    num(asNumber(r,"median_rules"),1)+'</td><td>'+num(asNumber(r,"max_wall_s"),2)+'s</td><td>'+
    num(asNumber(r,"models"))+'</td><td>'+esc(notes[id])+'</td></tr>';
 }).join("");
}
const prioritize=["OML51:openml_1169","OML51:openml_41027","OML51:openml_41162","OML51:openml_42732","OML51:openml_42733","OML51:openml_42734","UCI20:adult_income","OML51:openml_42742"];
const color=["#2d70a7","#bb5f30","#4a8271","#974e87","#b18132","#5488a4","#be6e80","#6c7d45","#835eaf"];
function scaling(rows){
 const g=$("scaleSvg");g.replaceChildren();axes(g,"CI 10k measured → conditional extrapolation, + CI full-size evidence",5);
 const scenario=$("scaleScenario").value,showAll=$("scaleDetail").value==="ALL_HIGH";
 const filtered=rows.filter(r=>r.scenario===scenario&&r.degenerate_ladder!=="True"&&r.many_rules==="True"
 &&(showAll||prioritize.includes(r.dataset)));
 const chartEnd=2.5e6;
 for(let i=0;i<filtered.length;i++){
  const r=filtered[i];const xFull=asNumber(r,"full_rows"),wall10=asNumber(r,"wall_10000_s"),exp=asNumber(r,"exponent");
  if(!(xFull>10000&&wall10>0))continue;
  const col=color[i%color.length],x2=Math.min(xFull,chartEnd),predAtEnd=wall10*Math.pow(x2/10000,exp);
  const start=coords(10000,wall10,5),end=coords(x2,Math.max(.1,Math.min(1e5,predAtEnd)),5);
  svg(g,"path",{d:"M"+start[0].toFixed(1)+","+start[1].toFixed(1)+"L"+end[0].toFixed(1)+","+end[1].toFixed(1),stroke:col,"stroke-width":2,fill:"none","stroke-dasharray":"6,5",opacity:.85});
  const m=svg(g,"circle",{cx:start[0],cy:start[1],r:6,fill:col});
  svg(m,"title",{},r.dataset+" / "+scenario+" 10k measured "+num(wall10,1)+"s; 10k rules "+num(asNumber(r,"rules_10000")));
  const fullX=coords(xFull,1,5)[0],ci=asNumber(r,"ci_full_median_s");
  if(ci!==null&&ci>0){const y=coords(xFull,ci,5)[1];
    const q=svg(g,"rect",{x:fullX-5,y:y-5,width:10,height:10,fill:col,stroke:"#fff","stroke-width":1});
    svg(q,"title",{},r.dataset+" CI full median of only "+r.ci_full_done+" successful models = "+num(ci,1)+"s");
  }
  if(asNumber(r,"ci_full_timeouts")>0)markX(g,fullX,coords(xFull,2700,5)[1],null);
  const label= r.dataset.split(":").slice(-1)[0];
  const ly=asNumber(r,"ci_full_timeouts")>0?coords(xFull,2700,5)[1]-11:end[1]-10;
  svg(g,"text",{x:Math.min(1000,Math.max(120,fullX-9)),y:Math.max(70,Math.min(450,ly)),fill:col,"font-size":12,"text-anchor":fullX>890?"end":"start"},label);
 }
}
const classOf=r=>r.degenerate_ladder==="True"?flag("退化梯度","caution"):Number(r.ci_full_timeouts)>0?flag("含設限 TIMEOUT","danger"):r.many_rules==="True"?flag("高規則數","caution"):flag("完成值");
function table(rows){
 const sc=$("tableScenario").value,filter=$("tableRisk").value;
 const val=rows.filter(r=>(sc==="ALL"||r.scenario===sc)&&
 (filter==="ALL"||filter==="TIMEOUT"&&Number(r.ci_full_timeouts)>0||
 filter==="HIGH"&&r.many_rules==="True"||filter==="DEGENERATE"&&r.degenerate_ladder==="True"));
 const arr=val.sort((a,b)=>Number(b.ci_full_timeouts)-Number(a.ci_full_timeouts)||
 Number(b.rules_10000)-Number(a.rules_10000));
 $("tableCount").textContent="顯示 "+arr.length+" / 48 組來源×分布；空的 CI Median 是「沒有成功模型／未觀測」，不是0秒。";
 $("scaleRows").innerHTML=arr.map(r=>{
 const tm=asNumber(r,"ci_full_median_s"),estimated=asNumber(r,"rows_reaching_2700s_cal");
 return '<tr><td><b>'+esc(r.dataset)+'</b></td><td>'+esc(r.scenario)+'</td>'+
 '<td>'+num(asNumber(r,"full_rows"))+'</td><td>'+num(asNumber(r,"rules_10000"))+'</td>'+
 '<td>'+num(asNumber(r,"wall_10000_s"),1)+'</td><td>'+num(asNumber(r,"ci_full_done"))+' / '+num(asNumber(r,"ci_full_timeouts"))+'</td>'+
 '<td>'+num(tm,1)+'</td><td>'+num(estimated)+'</td><td>'+classOf(r)+'</td></tr>';
 }).join("");
}
Promise.all([readCsvGzip("./per_source_observed.csv.gz"),readCsvGzip("./per_source_scaling.csv.gz")])
.then(([observed,scales])=>{
 if(observed.length!==181||scales.length!==48||scales.filter(x=>x.degenerate_ladder==="True").length!==11){
  throw Error("source count/degeneracy verification failure");
 }
 $("dataStatus").textContent="已驗證兩份來源檔 · 實測 181 個有成功模型的來源 · 48 組縮放組合（11 組退化） · 視覺化直接取自同一 gzip 原始 CSV";
 scatter(observed);scaling(scales);table(scales);
 for(const id of ["scaleScenario","scaleDetail"])$(id).addEventListener("change",()=>scaling(scales));
 for(const id of ["tableScenario","tableRisk"])$(id).addEventListener("change",()=>table(scales));
}).catch(err=>{
 $("dataStatus").textContent="未能驗證原始資料："+err.message+"。下方文字結論仍附 GitHub 原始來源，但圖表請勿當作已載入的驗證結果。";
});
})();