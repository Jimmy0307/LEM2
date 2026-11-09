"use strict";
/* Research evidence and browser-model results are deliberately separate. */
const $ = id=>document.getElementById(id);
const esc = s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pct=v=>v==null||!Number.isFinite(+v)?"未定義":(+v*100).toFixed(2)+"%";
const num=v=>v==null?"—":(+v).toLocaleString("zh-TW",{maximumFractionDigits:2});
const names=["FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH","POPULATION_STANDARD","POPULATION_GLOBAL"];
const metricText={accuracy:"Accuracy",balanced_accuracy:"Balanced Accuracy",macro_f1:"Macro-F1",coverage:"Coverage",conflict_case_rate:"Conflict rate",true_in_candidate_rate:"True-in-Candidate",rule_count:"Rule Count"};
let evidence=[],completed=new Set(),viewSeed=42,customInput=null,customResult=null,worker=null;

function parseCSV(text){
  text=String(text).replace(/^\ufeff/,"");
  let rows=[],r=[],field="",quoted=false;
  for(let i=0;i<text.length;i++){
    const c=text[i];
    if(c==='"'){
      if(quoted&&text[i+1]==='"'){field+='"';i++;}
      else quoted=!quoted;
    }else if(!quoted&&(c===","||c==="\n"||c==="\r")){
      r.push(field);field="";
      if(c!==","){if(r.some(x=>x!==""))rows.push(r);r=[];if(c==="\r"&&text[i+1]==="\n")i++;}
    }else field+=c;
  }
  if(quoted)throw new Error("CSV 引號未結束，無法正確解析。");
  if(r.length||field!==""){r.push(field);rows.push(r);}
  if(rows.length<2)throw new Error("CSV 需要表頭與至少一筆資料。");
  const columns=rows.shift().map(x=>x.trim());
  if(!columns.every(Boolean)||new Set(columns).size!==columns.length)throw new Error("CSV 欄名為空或重複。");
  for(const row of rows)if(row.length!==columns.length)throw new Error("CSV 欄位數與表頭不一致。");
  return {columns,rows:rows.filter(row=>row.some(v=>v.trim()!==""))};
}
function download(name,body,type="text/plain;charset=utf-8"){
  const blob=new Blob([body],{type}),url=URL.createObjectURL(blob),a=document.createElement("a");
  a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),200);
}
function setStatus(id,message,isError=false){$(id).textContent=message;$(id).className=isError?"loading":"proof";}
function mapRows(json){
  if(!json||!Array.isArray(json.columns)||!Array.isArray(json.rows))throw new Error("證據 JSON 格式不完整。");
  return json.rows.map(row=>Object.fromEntries(json.columns.map((col,i)=>[col,row[i]])));
}
function validateEvidence(rows){
  const perSeed=new Map(),keys=new Set();
  for(const r of rows){
    const seed=Number(r.seed),key=[seed,r.dataset,r.split_mode,r.system,r.client_count,r.selection_policy].join("|");
    if(!Number.isInteger(seed)||seed<1||seed>42||keys.has(key))throw new Error("8,820 主表有 Seed 錯誤或重複實驗鍵："+key);
    keys.add(key);
    if(!perSeed.has(seed))perSeed.set(seed,[]);
    perSeed.get(seed).push(r);
  }
  const verified=new Set();
  for(let seed=1;seed<=42;seed++){
    const one=perSeed.get(seed)||[];
    const none=one.filter(r=>r.selection_policy==="NONE").length;
    if(one.length===210&&none===30&&one.length-none===180)verified.add(seed);
  }
  return verified;
}
async function loadBaseline(){
  try{
    const response=await fetch("./data/baseline_8820.json",{cache:"no-cache"});
    if(!response.ok)throw Error("HTTP "+response.status+"，請確認 GitHub Actions 已發布資料");
    const j=await response.json();
    evidence=mapRows(j);
    completed=validateEvidence(evidence);
    updateGrid();updateEvidence();
  }catch(error){
    $("seedStatus").textContent="載入失敗："+error.message;
    $("summaryCards").innerHTML='<div class="metric">無法驗證原始實測資料。請從 GitHub 下載正式 CSV；目前不會把 Seed 標成已完成。</div>';
    updateGrid();
  }
}
function updateGrid(){
  const el=$("seedGrid");el.replaceChildren();
  for(let seed=1;seed<=42;seed++){
    const button=document.createElement("button");
    button.type="button";button.className="seed-btn "+(completed.has(seed)?"measured":"pending")+(seed===viewSeed?" selected":"");
    button.textContent=String(seed);button.title="Seed "+seed+"："+(completed.has(seed)?"210 個經驗證配置":"資料未完整載入");
    button.setAttribute("aria-pressed",String(seed===viewSeed));
    button.onclick=()=>{viewSeed=seed;$("csvSeed").value=String(seed);updateGrid();updateEvidence();};
    el.append(button);
  }
  $("seedStatus").textContent="經驗證 Seeds "+completed.size+"/42；待測／缺證據 "+(42-completed.size)+"/42";
}
function selection(){
  return {
    dataset:$("dataset").value,split:$("split").value,system:$("system").value,
    clients:$("clients").value,policy:$("policy").value,metric:$("metric").value
  };
}
function relevantRows(seed,cfg){
  return evidence.filter(r=>
    Number(r.seed)===seed&&r.split_mode===cfg.split&&r.system===cfg.system&&
    r.selection_policy===cfg.policy&&(cfg.dataset==="ALL"||r.dataset===cfg.dataset)&&
    (cfg.system==="CENTRALIZED"||cfg.clients==="ALL"||Number(r.client_count)===+cfg.clients)
  );
}
function avg(rows,field){const values=rows.map(x=>x[field]).filter(v=>v!==null&&v!==undefined&&Number.isFinite(+v)).map(Number);return values.length?values.reduce((a,b)=>a+b,0)/values.length:null;}
function svgElement(tag,attrs={},text=null){
  const e=document.createElementNS("http://www.w3.org/2000/svg",tag);
  Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,String(v)));
  if(text!==null)e.textContent=text;
  return e;
}
function lineChart(values,metric,selected){
  const svg=$("seedChart");svg.replaceChildren();
  const numbers=values.filter(v=>v.value!==null).map(v=>v.value);
  if(!numbers.length){svg.append(svgElement("text",{x:30,y:60,fill:"#617585"},"所選指標尚未定義（例如 NONE 的 Accuracy）"));return;}
  const min=metric==="rule_count"?Math.max(0,Math.floor(Math.min(...numbers)*.85)):0;
  const max=metric==="rule_count"?Math.max(1,Math.ceil(Math.max(...numbers)*1.05)):1;
  const x=n=>30+(n-1)*870/41,y=v=>225-(v-min)/(max-min||1)*192;
  for(let k=0;k<5;k++){
    const v=min+(max-min)*k/4;
    const yy=y(v);
    svg.append(svgElement("line",{x1:30,y1:yy,x2:912,y2:yy,stroke:"#e4edf0","stroke-width":1}));
    svg.append(svgElement("text",{x:25,y:yy+4,fill:"#78909b","text-anchor":"end","font-size":10},metric==="rule_count"?v.toFixed(0):(v*100).toFixed(0)+"%"));
  }
  const pts=values.filter(v=>v.value!=null).map(v=>x(v.seed)+","+y(v.value)).join(" ");
  svg.append(svgElement("polyline",{points:pts,fill:"none",stroke:"#168580","stroke-width":2.5,"stroke-linejoin":"round"}));
  values.forEach(z=>{
    if(z.value==null)return;
    const c=svgElement("circle",{cx:x(z.seed),cy:y(z.value),r:z.seed===selected?5:3,fill:z.seed===selected?"#cf9440":"#1c8e84"});
    c.append(svgElement("title",{},"Seed "+z.seed+"；"+metricText[metric]+"="+(metric==="rule_count"?num(z.value):pct(z.value))));
    svg.append(c);
  });
  [1,7,14,21,28,35,42].forEach(n=>svg.append(svgElement("text",{x:x(n),y:248,fill:"#627586","text-anchor":"middle","font-size":11},String(n))));
}
function updateEvidence(){
  if(!evidence.length)return;
  const cfg=selection(),table=[],allAvg=[];
  for(let seed=1;seed<=42;seed++){
    const rows=relevantRows(seed,cfg);
    const value=avg(rows,cfg.metric);
    const rec={seed,rows:rows.length,value,cov:avg(rows,"coverage"),conf:avg(rows,"conflict_case_rate"),rules:avg(rows,"rule_count")};
    table.push(rec);if(value!==null)allAvg.push(value);
  }
  lineChart(table,cfg.metric,viewSeed);
  const current=table.find(r=>r.seed===viewSeed);
  const isPercent=cfg.metric!=="rule_count";
  const cards=[
   ["研究配置","42 Seeds × 210","3 資料集 × 2 分割 × 5 拓樸 × 7 模式"],
   ["完整 Seed",completed.size+"/42","依實測資料鍵值逐一檢查"],
   ["目前 Seed "+viewSeed,current.value===null?"未定義":isPercent?pct(current.value):num(current.value),metricText[cfg.metric]],
   ["42 Seeds 等權平均",allAvg.length?(isPercent?pct(allAvg.reduce((a,b)=>a+b,0)/allAvg.length):num(allAvg.reduce((a,b)=>a+b,0)/allAvg.length)):"未定義","僅相同因素條件下比較"]
  ];
  $("summaryCards").innerHTML=cards.map(([label,v,detail])=>'<div class="metric"><small>'+esc(label)+'</small><strong>'+esc(v)+'</strong><span>'+esc(detail)+'</span></div>').join("");
  $("seedTable").innerHTML=table.map(r=>'<tr'+(r.seed===viewSeed?' style="background:#eaf5f1"':'')+'><td><button data-seedrow="'+r.seed+'">'+r.seed+'</button></td><td class="num">'+r.rows+'</td><td class="num">'+(r.value===null?'未定義':isPercent?pct(r.value):num(r.value))+'</td><td class="num">'+pct(r.cov)+'</td><td class="num">'+pct(r.conf)+'</td><td class="num">'+num(r.rules)+'</td></tr>').join("");
}
["dataset","split","system","clients","policy","metric"].forEach(k=>$(k).addEventListener("change",()=>{if($("system").value==="CENTRALIZED")$("clients").disabled=true;else $("clients").disabled=false;updateEvidence();}));
$("seedTable").addEventListener("click",e=>{const b=e.target.closest("[data-seedrow]");if(b){viewSeed=+b.dataset.seedrow;$("csvSeed").value=String(viewSeed);updateGrid();updateEvidence();}});
$("baselineCsv").onclick=()=>{
  const cfg=selection(),rows=evidence.filter(r=>r.split_mode===cfg.split&&r.system===cfg.system&&r.selection_policy===cfg.policy&&(cfg.dataset==="ALL"||r.dataset===cfg.dataset)&&(cfg.system==="CENTRALIZED"||cfg.clients==="ALL"||Number(r.client_count)===+cfg.clients));
  if(!rows.length)return;
  const columns=Object.keys(rows[0]);
  const csv=[columns.join(","),...rows.map(r=>columns.map(k=>r[k]??"").join(","))].join("\n");
  download("LEM2_42seed_filtered.csv","\ufeff"+csv,"text/csv;charset=utf-8");
};
function setupCSVSelectors(){
  const s=$("csvSeed");for(let seed=1;seed<=42;seed++){const opt=document.createElement("option");opt.value=String(seed);opt.textContent="Seed "+seed;s.append(opt);}s.value="42";
}
function acceptCustom(inp,label){
  if(inp.rows.length>600||inp.columns.length>11)throw Error("瀏覽器模型支援至多 600 筆、最多 8 個條件欄。大資料請使用 GitHub 命令列。");
  customInput=inp;customResult=null;
  $("downloadModel").disabled=true;
  $("modelResults").hidden=true;
  const select=$("csvTarget");select.replaceChildren();
  inp.columns.forEach(c=>{const opt=document.createElement("option");opt.value=c;opt.textContent=c;select.append(opt);});
  select.value=inp.columns.find(x=>["class","label","decision","target"].includes(x.trim().toLowerCase()))||inp.columns.at(-1);
  $("runButton").disabled=false;
  $("csvInfo").textContent=label+"："+inp.rows.length+" 筆、"+inp.columns.length+" 欄；預設決策欄位為「"+select.value+"」。";
  setStatus("runStatus","已匯入資料。選擇 Seed、80/20 與 C 後，點擊「開始原始 LEM2 試算」。");
}
$("csvFile").onchange=async e=>{
  try{
    const file=e.target.files[0];if(!file)return;
    if(file.size>1.5*1024*1024)throw Error("CSV 超過 1.5 MB，請用命令列版本。");
    const txt=await file.text();
    acceptCustom(parseCSV(txt),file.name);
  }catch(err){customInput=null;$("runButton").disabled=true;setStatus("runStatus",err.message,true);}
};
$("demoButton").onclick=()=>{
  const rows=[];for(let a=1;a<=3;a++)for(let b=1;b<=3;b++)for(let c=1;c<=3;c++)for(let d=1;d<=3;d++)
    rows.push([String(a),String(b),String(c),String(d),a*b===c*d?"B":a*b>c*d?"L":"R"]);
  acceptCustom({columns:["left_weight","left_distance","right_weight","right_distance","class"],rows},"內建教學案例 81 筆");
};
function ruleAsText(rule){const conditions=rule.if||[];return "IF "+(conditions.map(x=>x[0]+"="+x[1]).join(" AND ")||"TRUE")+" THEN "+rule.then;}
function scoreTable(scores){
  if(!scores.length)return "<p>沒有候選規則，直接使用多數類別 Fallback。</p>";
  const keys=["decision","rule_hits","T","U","N","P","STANDARD_VOTING","GLOBAL_STRENGTH","POPULATION_STANDARD","POPULATION_GLOBAL"];
  return '<div class="table-wrap"><table><thead><tr>'+keys.map(k=>'<th>'+esc(k)+'</th>').join("")+'</tr></thead><tbody>'+
    scores.map(r=>'<tr>'+keys.map(k=>'<td>'+esc(typeof r[k]==="number"?Number(r[k]).toFixed(k==="decision"?0:4):r[k])+'</td>').join("")+'</tr>').join("")+
    "</tbody></table></div>";
}
function renderAssignment(result){
  const entries=result.assignments||[];
  const labels=[...new Set(entries.map(x=>x.decision))].sort();
  const colors={Test:"#d2a14a",Centralized:"#3c8fa0",Client_1:"#188777",Client_2:"#487cbb",Client_3:"#9b78b4",Client_4:"#d78065",Client_5:"#83965c"};
  const summaries=labels.map(label=>{
    const subset=entries.filter(x=>x.decision===label);
    const counts={};
    for(const r of subset){const group=r.in_train?r.client:"Test";counts[group]=(counts[group]||0)+1;}
    return {label,count:subset.length,counts};
  });
  $("assignmentBars").innerHTML=summaries.map(s=>{
    const bars=Object.entries(s.counts).map(([group,n])=>
      '<div title="'+esc(group)+': '+n+' 筆" style="background:'+colors[group]+';flex:'+n+'"></div>').join("");
    const caption=Object.entries(s.counts).map(([group,n])=>esc(group)+":"+n).join(" · ");
    return '<div class="metric"><small>類別 '+esc(s.label)+'</small><strong>'+s.count+' 筆</strong><div class="chartbar">'+bars+'</div><span>'+caption+'</span></div>';
  }).join("");
  $("assignmentTable").innerHTML=entries.slice(0,600).map(r=>
    '<tr><td>'+r.row_id+'</td><td>'+esc(r.decision)+'</td><td>'+(r.in_train?"是":"否")+'</td><td>'+(r.in_evaluation?"是":"否")+'</td><td>'+esc(r.client)+'</td></tr>').join("");
}
$("downloadAssignments").onclick=()=>{
  if(!customResult)return;
  const cols=["row_id","decision","in_train","in_evaluation","client"];
  const csv=[cols.join(","),...(customResult.assignments||[]).map(r=>cols.map(k=>
    '"'+String(r[k]??"").replace(/"/g,'""')+'"').join(","))].join("\n");
  download("LEM2_exact_python_row_assignments.csv","\ufeff"+csv,"text/csv;charset=utf-8");
};
function renderModel(result){
  customResult=result;
  renderAssignment(result);
  $("modelResults").hidden=false;$("downloadModel").disabled=false;
  $("modelCards").innerHTML=[
    ["原始列數",result.dataset_rows,"使用者提供"],
    ["Train / Test",result.train_rows+" / "+result.test_rows,result.split==="FULL_DATA"?"同資料回代（非泛化）":"80/20 未見資料"],
    ["Pure LEM2 Rule Set",result.rule_count,"不等於模型 Accuracy"],
    ["GS Balanced Accuracy",pct(result.metrics.GLOBAL_STRENGTH.balanced_accuracy),"六種策略之一"]
  ].map(x=>'<div class="metric"><small>'+esc(x[0])+'</small><strong>'+esc(x[1])+'</strong><span>'+esc(x[2])+'</span></div>').join("");
  $("modelPolicies").innerHTML=names.map(p=>{
    const m=result.metrics[p],e=result.error_decomposition[p]||{};
    return '<tr><td>'+esc(p)+'</td><td class="num">'+pct(m.accuracy)+'</td><td class="num">'+pct(m.balanced_accuracy)+'</td><td class="num">'+pct(m.macro_f1)+'</td><td class="num">'+num(e.CANDIDATE_PRESENT_BUT_SELECTED_WRONG||0)+'</td><td class="num">'+num(e.NO_MATCH_FALLBACK_CORRECT||0)+' / '+num(e.NO_MATCH_FALLBACK_WRONG||0)+'</td></tr>';
  }).join("");
  $("modelClasses").innerHTML=result.classes.map(c=>'<tr><td>'+esc(c.decision)+'</td><td class="num">'+c.n+'</td><td class="num">'+pct(c.coverage)+'</td><td class="num">'+pct(c.candidate_coverage)+'</td><td class="num">'+pct(c.conflict_rate)+'</td><td class="num">'+pct(c.recall_GLOBAL_STRENGTH)+'</td></tr>').join("");
  drawPolicyBars(result);renderCases();$("modelResults").scrollIntoView({behavior:"smooth",block:"start"});
}
function drawPolicyBars(result){
  const svg=$("modelChart");svg.replaceChildren();
  const colors=["#177c79","#d0953f"],max=1;
  const keys=["accuracy","balanced_accuracy"];
  for(let k=0;k<5;k++){
    const yy=230-k*45;svg.append(svgElement("line",{x1:25,y1:yy,x2:920,y2:yy,stroke:"#e4e9ed"}));
    svg.append(svgElement("text",{x:10,y:yy+4,"font-size":10,fill:"#71818c"},k*25+"%"));
  }
  names.forEach((p,i)=>{
    const g=result.metrics[p];
    keys.forEach((key,j)=>{
      const h=(g[key]||0)*180;
      const r=svgElement("rect",{x:65+i*146+j*37,y:230-h,width:30,height:h,rx:3,fill:colors[j]});
      r.append(svgElement("title",{},p+" "+key+" "+pct(g[key])));svg.append(r);
    });
    svg.append(svgElement("text",{x:99+i*146,y:252,"font-size":9,"text-anchor":"middle",fill:"#596976"},p.replace("POPULATION","POP").replace("_VOTING","").replace("GLOBAL_STRENGTH","GLOBAL")));
  });
  svg.append(svgElement("text",{x:735,y:16,fill:colors[0],"font-size":13},"■ Accuracy"));
  svg.append(svgElement("text",{x:830,y:16,fill:colors[1],"font-size":13},"■ BA"));
}
function visibleCases(){
  if(!customResult)return[];
  const policy=$("casePolicy").value,filter=$("caseFilter").value;
  return customResult.cases.filter(c=>{
    const o=c.outcomes[policy];
    return filter==="ALL"||(filter==="CONFLICT"&&c.conflict)||
      (filter==="NO_MATCH"&&c.matched_count===0)||
      (filter==="TRUE_ABSENT"&&o.error_type==="TRUE_CLASS_NOT_CANDIDATE")||
      (filter==="WRONG_RANKING"&&o.error_type==="CANDIDATE_PRESENT_BUT_SELECTED_WRONG")||
      (filter==="CORRECT"&&o.correct);
  });
}
function renderCases(){
  if(!customResult)return;const policy=$("casePolicy").value,values=visibleCases();
  $("caseTable").innerHTML=values.slice(0,300).map(c=>{
    const o=c.outcomes[policy],diagnosis=o.error_type;
    return '<tr data-case="'+c.row_id+'"><td><button data-case="'+c.row_id+'">'+c.row_id+'</button></td><td>'+esc(c.true)+'</td><td>'+esc(c.candidates.join(", ")||"無")+'</td><td class="num">'+c.matched_count+'</td><td>'+(c.conflict?'<span class="chip warn">Conflict</span>':'—')+'</td><td>'+esc(o.winner)+'</td><td><span class="chip '+(o.correct?"good":"bad")+'">'+esc(diagnosis)+'</span></td></tr>';
  }).join("");
  if(values.length>300){$("caseDetail").textContent="已顯示前 300 筆；完整逐筆證據請下載 JSON。";}
  else $("caseDetail").textContent="點選任一列查看實際匹配規則、候選得分、最後 Winner。共 "+values.length+" 筆符合目前篩選。";
}
$("casePolicy").onchange=renderCases;$("caseFilter").onchange=renderCases;
$("caseTable").onclick=e=>{
  const row=e.target.closest("[data-case]");if(!row||!customResult)return;
  const c=customResult.cases.find(x=>x.row_id===+row.dataset.case);if(!c)return;
  const meta="<b>Row ID "+c.row_id+"</b>｜真實類別："+esc(c.true)+"｜候選："+esc(c.candidates.join(", ")||"無")+
    "｜Conflict："+(c.conflict?"是":"否")+"｜多數類別 Fallback："+esc(c.default_class);
  const outcomes="<h3>六種方法的 Winner</h3><div class='table-wrap'><table><thead><tr><th>策略</th><th>Winner</th><th>正確?</th><th>錯誤型態</th></tr></thead><tbody>"+
    names.map(p=>'<tr><td>'+p+'</td><td>'+esc(c.outcomes[p].winner)+'</td><td>'+(c.outcomes[p].correct?"✓":"✕")+'</td><td>'+esc(c.outcomes[p].error_type)+'</td></tr>').join("")+"</tbody></table></div>";
  const rules="<details open><summary>真正命中的 IF–THEN 規則（最多 50 條）</summary><ol>"+c.matched_rules.map(r=>'<li><code>'+esc(ruleAsText(r))+'</code>（weight='+num(r.weight)+'）</li>').join("")+"</ol></details>";
  $("caseDetail").innerHTML=meta+"<p>實際輸入："+esc(JSON.stringify(c.features))+"</p>"+outcomes+
    "<h3>每個類別的支持人口與六種計分</h3>"+scoreTable(c.scores)+rules;
};
$("runButton").onclick=()=>{
  if(!customInput)return;
  const b=$("runButton");b.disabled=true;
  $("modelResults").hidden=true;
  setStatus("runStatus","初始化運算中；模型計算在瀏覽器記憶體內進行。");
  if(worker)worker.terminate();
  worker=new Worker("./browser_engine_worker.js",{type:"module"});
  worker.onmessage=({data})=>{
    if(data.kind==="status")setStatus("runStatus",data.message);
    else if(data.kind==="error"){setStatus("runStatus","試算失敗："+data.message,true);b.disabled=false;}
    else if(data.kind==="result"){
      setStatus("runStatus","原始 Python LEM2 試算完成。這是使用者 CSV 的新實驗，不會混入 8,820 筆已封存主矩陣。");
      b.disabled=false;renderModel(data.result);
    }
  };
  worker.onerror=e=>{setStatus("runStatus","模型工作執行器錯誤："+(e.message||"請檢查瀏覽器網路限制"),true);b.disabled=false;};
  worker.postMessage({kind:"execute",payload:{
    columns:customInput.columns,rows:customInput.rows,target:$("csvTarget").value,
    seed:Number($("csvSeed").value),split:$("csvSplit").value,clients:Number($("csvClients").value)
  }});
};
$("downloadModel").onclick=()=>{if(customResult)download("LEM2_custom_csv_result.json",JSON.stringify(customResult,null,2),"application/json;charset=utf-8");};
setupCSVSelectors();updateGrid();loadBaseline();
