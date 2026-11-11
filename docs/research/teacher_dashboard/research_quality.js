/* Teacher remediation decision board, v3.
 * Independent evidence paths:
 *  - model_comparison: only 42-seed, 3-dataset equal-weight, HOLDOUT_80_20
 *  - conflict_triage: original row-level evidence, reconciled with 8820 metrics
 *  - hayes_remediation: separate, non-frozen UCI official/group protocols
 */
(() => {
"use strict";
const $=id=>document.getElementById(id);
const S="http://www.w3.org/2000/svg";
const metnames={balanced_accuracy:"Balanced Accuracy",accuracy:"Accuracy",macro_f1:"Macro-F1",coverage:"Coverage",conflict_case_rate:"Conflict"};
const sh={FIRST_MATCH:"FIRST",SIMPLE_VOTING:"SIMPLE",STANDARD_VOTING:"STD",GLOBAL_STRENGTH:"GS",POPULATION_STANDARD:"PS",POPULATION_GLOBAL:"PG"};
const colors={ink:"#234457",teal:"#167d78",blue:"#427d9f",gold:"#d09544",gray:"#8796a0",red:"#bb6860",green:"#27917b"};
let ranking=null,triage=null,hayes=null;
const pct=x=>x==null||!Number.isFinite(x)?"未定義":(100*x).toFixed(2)+"%";
const pp=x=>x==null||!Number.isFinite(x)?"未定義":(100*x).toFixed(2)+" pp";
const fmt=x=>x==null||!Number.isFinite(x)?"—":(100*x).toFixed(2)+"%";
const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function svg(name,attrs={},content){const n=document.createElementNS(S,name);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,String(v)));if(content!==undefined)n.textContent=content;return n;}
function note(parent,x,y,t,attributes={}){parent.append(svg("text",{x,y,"font-size":12,fill:"#607788",...attributes},t));}
function frame(graph){graph.replaceChildren();}
function axes(g,x0,y0,w,h,min=0,max=1){for(let i=0;i<=4;i++){let v=min+(max-min)*i/4,yy=y0+h-(v-min)/(max-min)*h;g.append(svg("line",{x1:x0,y1:yy,x2:x0+w,y2:yy,stroke:"#e6edf0"}));note(g,x0-10,yy+4,(v*100).toFixed(0)+"%",{"text-anchor":"end","font-size":11});}}
function present(list){return list.filter(v=>v!=null&&Number.isFinite(v));}
function average(list){let a=present(list);return a.length?a.reduce((x,y)=>x+y,0)/a.length:null;}
const globalScope=()=>({dataset:$("gDataset").value,seed:$("gSeed").value,split:$("gSplit").value,
    system:$("gSystem").value,client:Number($("gClient").value),policy:$("gPolicy").value});
function namescope(row){return (row.system==="CENTRALIZED"?"集中式":"聯邦 C"+row.client_count)+" × "+(sh[row.policy]||row.policy);}

function datasetRows(){
    const ds=$("gDataset").value;
    if(!ranking)return[];
    if(ds==="ALL")return ranking.overall_3_dataset_equal||[];
    return (ranking.by_dataset||[]).filter(r=>r.dataset===ds);
}
function renderBest(){
    if(!ranking)return;
    let all=datasetRows(),metric=$("bestMetric").value;
    let ranked=[...all].sort((a,b)=>(b[metric]-a[metric])||(a.conflict_case_rate-b.conflict_case_rate)||a.client_count-b.client_count);
    const winner=ranked[0],second=ranked[1];
    const notes=[$("gDataset").value==="ALL"?"三個資料集等權":"單一資料集 "+$("gDataset").value,
                 "42 Seeds 均值","全部五種學習架構 × 六策略","80/20 未見資料"];
    $("bestScope").textContent=notes.join(" · ");
    if($("gSplit").value==="FULL_DATA"){
      $("bestScope").textContent+="；你目前的流程選的是回代，這裡仍然只使用 80/20 排名，避免不公平比較";
    }
    $("bestKpis").innerHTML=[
      ["第一名",namescope(winner),metnames[metric]+" = "+pct(winner[metric])],
      ["相對第二名優勢",pp(winner[metric]-second[metric]),"此為描述性平均差值，尚非跨獨立資料集顯著性"],
      ["第一名的 Conflict",pct(winner.conflict_case_rate),"候選衝突率；不等於分類錯誤"],
      ["第一名的 Coverage",pct(winner.coverage),"規則命中比例；不等於模型準確率"]
    ].map(([n,v,foot])=>'<div class="kpi"><small>'+esc(n)+'</small><strong class="best-kpi-value">'+esc(v)+'</strong><span>'+esc(foot)+'</span></div>').join("");
    const top=ranked.slice(0,10);
    $("bestRows").innerHTML=top.map((r,i)=>{
      const diff=(winner[metric]-r[metric])*100;
      return '<tr'+(i===0?' class="selected-row"':'')+'><td>'+(i+1)+'</td><td>'+esc(namescope(r))+'</td>'+
      '<td class="n"><b>'+pct(r[metric])+'</b></td><td class="n">'+pct(r.accuracy)+'</td>'+
      '<td class="n">'+pct(r.balanced_accuracy)+'</td><td class="n">'+pct(r.macro_f1)+'</td>'+
      '<td class="n">'+pct(r.conflict_case_rate)+'</td><td class="n">'+pct(r.coverage)+'</td>'+
      '<td class="n">'+diff.toFixed(2)+' pp</td></tr>';
    }).join("");
    const independent=["Balance Scale","Car Evaluation","Hayes-Roth"];
    $("datasetWinners").innerHTML=independent.map(ds=>{
      const candidates=ranking.by_dataset.filter(r=>r.dataset===ds);
      const win=[...candidates].sort((a,b)=>(b[metric]-a[metric])||(a.conflict_case_rate-b.conflict_case_rate))[0];
      const caveat=ds==="Hayes-Roth"?"原 132 筆反覆 80/20；請另看官方與分組不重疊測試":"固定資料集 42 Seeds 切分；不代表跨資料集普遍性";
      return '<tr><td>'+esc(ds)+'</td><td><b>'+esc(namescope(win))+'</b></td>'+
             '<td class="n">'+pct(win[metric])+'</td><td class="n">'+pct(win.conflict_case_rate)+'</td>'+
             '<td class="n">'+pct(win.coverage)+'</td><td>'+esc(caveat)+'</td></tr>';
    }).join("");
    const pareto=all.filter(a=>!all.some(b=>b!==a&&b[metric]>=a[metric]-1e-12&&
      b.conflict_case_rate<=a.conflict_case_rate+1e-12&&
      (b[metric]>a[metric]+1e-12||b.conflict_case_rate<a.conflict_case_rate-1e-12)));
    pareto.sort((a,b)=>a.conflict_case_rate-b.conflict_case_rate);
    $("paretoCards").innerHTML=pareto.map(a=>
        '<div class="card"><small>非支配折衷方案（Pareto）</small><h3>'+esc(namescope(a))+'</h3>'+
        '<p><b>'+pct(a[metric])+'</b> · '+esc(metnames[metric])+'</p>'+
        '<p>Conflict：'+pct(a.conflict_case_rate)+' · Coverage：'+pct(a.coverage)+'</p>'+
        '<p class="metric-note">找不到另一個配置同時具有更高（或相等）'+esc(metnames[metric])+
        '及更低（或相等）Conflict，並至少一項嚴格更好。</p></div>').join("");
    $("bestInterpretation").innerHTML=
      '以 <b>'+esc(metnames[metric])+'</b> 為決策目標，<b>'+esc(namescope(winner))+'</b> 暫列第一（<b>'+pct(winner[metric])+'</b>）。'+
      '但其衝突率 <b>'+pct(winner.conflict_case_rate)+'</b>，覆蓋率 <b>'+pct(winner.coverage)+'</b>。'+
      '排名只對上述三資料集（或指定單一資料集）、固定分層切分有效；不表示它在非 IID、官方 28 筆測試、其他資料集或部署成本下必然最好。';
    drawBestScatter(all,metric,winner);
}
function drawBestScatter(entries,metric,winner){
    const g=$("bestScatter");frame(g);
    const x0=83,y0=28,w=890,h=315;const xmax=1,ymax=1;
    axes(g,x0,y0,w,h,0,1);
    for(let j=0;j<=4;j++){let x=x0+j*w/4;g.append(svg("line",{x1:x,y1:y0,x2:x,y2:y0+h,stroke:"#eaf0f3"}));note(g,x,y0+h+19,String(j*25)+"%",{"text-anchor":"middle"});}
    entries.forEach(r=>{
      const x=x0+r.conflict_case_rate*w,y=y0+(1-r[metric])*h;
      const isBest=r===winner;
      const circle=svg("circle",{cx:x,cy:y,r:isBest?9:5,fill:isBest?colors.gold:r.system==="CENTRALIZED"?colors.blue:colors.teal,
        stroke:isBest?"#845b2b":"#fff","stroke-width":isBest?3:1,role:"img"});
      circle.append(svg("title",{},namescope(r)+"\n"+metnames[metric]+" "+pct(r[metric])+
                            "\nConflict "+pct(r.conflict_case_rate)+"\nCoverage "+pct(r.coverage)));
      g.append(circle);
      if(isBest)note(g,Math.min(x+13,770),Math.max(y-15,28),"第一名："+namescope(r),{fill:"#815521","font-size":13,"font-weight":"bold"});
    });
    note(g,x0+w/2,392,"候選衝突率（愈低表示規則歧義較少）",{"text-anchor":"middle","font-size":14});
    note(g,16,16,"縱軸："+metnames[metric]+"（愈高愈好）",{"font-size":13,fill:"#2c6379"});
    note(g,740,22,"● Centralized",{"font-size":12,fill:colors.blue});
    note(g,860,22,"● Federated",{"font-size":12,fill:colors.teal});
}
function triageRows(){
    if(!triage)return[];
    const s=globalScope();
    return triage.rows.filter(r=>
      (s.dataset==="ALL"||r.dataset===s.dataset)&&
      (s.seed==="ALL"||Number(r.seed)===Number(s.seed))&&
      r.split_mode===s.split && r.system===s.system &&
      (s.system==="CENTRALIZED"||Number(r.client_count)===s.client) &&
      r.policy===s.policy);
}
const CASE_GROUPS=[
 ["NO_MATCH","no_match_correct","no_match_wrong","#e5eaef"],
 ["有規則但正解不在候選","matched_absent_nonconflict","matched_absent_conflict","#d78985"],
 ["候選含正解、無衝突","matched_present_nonconflict_correct","matched_present_nonconflict_wrong","#4f94ac"],
 ["候選含正解、發生衝突","matched_present_conflict_correct","matched_present_conflict_wrong","#1f8c79"]
];
function renderTriage(){
    if(!triage)return;
    const a=triageRows();if(!a.length){$("triageStatus").textContent="此條件沒有逐筆證據";return;}
    const total=x=>average(a.map(r=>r[x]/r.evaluation_rows));
    const rows=CASE_GROUPS.map(([name,good,bad,color])=>({
        name,color,good:total(good),bad:total(bad),
        total:total(good)+total(bad)
    }));
    let fractions=rows.map(r=>r.total),sum=fractions.reduce((a,b)=>a+b,0);
    if(Math.abs(sum-1)>1e-9){$("triageStatus").textContent="資料分解不一致，拒絕顯示。";return;}
    const s=globalScope();
    $("triageStatus").textContent="核對來源：42 Seeds 逐筆規則證據／"+a.length+" 組相同因素配置；比例為各配置等權平均。";
    let goodConflict=total("matched_present_conflict_correct");
    let wrongConflict=total("matched_present_conflict_wrong");
    let missingConflict=total("matched_absent_conflict");
    let denominator=goodConflict+wrongConflict+missingConflict;
    const cf=denominator?goodConflict/denominator:null;
    const solv=goodConflict+wrongConflict?goodConflict/(goodConflict+wrongConflict):null;
    const noMatch=rows[0].total;
    $("triageMetrics").innerHTML=[
       ["完全無規則命中",pct(noMatch),"接 Fallback；既可能對也可能錯"],
       ["Conflict 物件比例",pct(denominator),"同時匹配兩個以上不同決策類別"],
       ["衝突子集最終答對率",pct(cf),"分母＝全部衝突物件"],
       ["可解衝突的條件正確率",pct(solv),"分母＝衝突且真實類別在 Candidate；離線 oracle 診斷"]
    ].map(([n,v,f])=>'<div class="kpi"><small>'+esc(n)+'</small><strong>'+esc(v)+'</strong><span>'+esc(f)+'</span></div>').join("");
    const stack=$("triageStack");stack.innerHTML=rows.map(r=>
      '<div class="triage-track" style="flex:'+Math.max(r.total,.001)+';background:'+r.color+'" title="'+esc(r.name)+pct(r.total)+'"></div>').join("");
    $("triageLegend").innerHTML=rows.map(r=>'<div class="triage-legend-item"><span class="triage-dot" style="background:'+r.color+'"></span>'+
      esc(r.name)+' <b>'+pct(r.total)+'</b>（其中答對 '+pct(r.good)+'、答錯 '+pct(r.bad)+'，均以全部測試物件為分母）</div>').join("");
    $("triageConflictBar").innerHTML=[
       ["正解不在候選",missingConflict,colors.red],
       ["正解在候選但選錯",wrongConflict,colors.gold],
       ["正解在候選且選對",goodConflict,colors.teal]
    ].map(([name,value,color])=>'<div class="triage-track" style="flex:'+Math.max(value,.0001)+';background:'+color+'" title="'+esc(name)+'：'+pct(denominator?value/denominator:null)+'"></div>').join("");
    $("triageConflictTable").innerHTML=[
      ["候選規則沒提出正解",missingConflict],
      ["候選含正解，但分類方法選錯",wrongConflict],
      ["候選含正解，分類方法選對",goodConflict]
    ].map(([n,v])=>'<tr><td>'+esc(n)+'</td><td class="n">'+pct(denominator?v/denominator:null)+'</td><td class="n">'+pct(v)+'</td></tr>').join("");
    $("triageDecision").innerHTML='<b>先看哪一層需要改善？</b> '+
      (missingConflict>wrongConflict?
       "此條件下衝突物件中，缺少正確候選的比例較高，應優先檢查局部 LEM2、Reduct、資料分配；單換投票器無法恢復缺失候選。":
       "此條件下衝突物件較多能提出正確候選，但仍可能選錯，應比較六策略的 T／U／N 支持度與 Winner。")+
      ' <b>注意：</b>是否有「正解候選」只在已知真實標籤的離線測試中可診斷，不可直接當成上線分類決策訊號。';
}
function renderProtocols(){
    if(!hayes)return;
    const met=$("protocolMetric").value,policy=$("gPolicy").value;
    const src=ranking?.by_dataset||[];
    const base=(client,met)=>src.find(x=>x.dataset==="Hayes-Roth"&&
         x.client_count===client&&x.policy===policy)?.[met]??null;
    const protocols=[
      ["原 132 筆重複 80/20",null,"基準 42 Seeds，Test=26；Train/Test 可能特徵重疊"],
      ["官方固定 132／28","OFFICIAL_132_28","官方另給 28 筆；不是從 132 筆隨機切出"],
      ["特徵組合不重疊", "GROUP_DISJOINT_80_20","按四個模型條件屬性分組，Test=24"]
    ];
    const grid=$("protocolRows");grid.innerHTML="";
    let totals=[];
    for(const client of [0,2,3,4,5]){
       let v=protocols.map(([name,tag])=>tag?hayes.summary.find(x=>x.holdout_protocol===tag&&x.client_count===client&&x.policy===policy)?.[met]:base(client,met));
       totals.push({client,vals:v});
    }
    grid.innerHTML=totals.map(o=>'<tr><td>'+(o.client===0?"集中式":"聯邦 C"+o.client)+'</td>'+
             o.vals.map(v=>'<td class="n">'+pct(v)+'</td>').join("")+
             '<td>'+esc(sh[policy])+'</td></tr>').join("");
    const g=$("protocolChart");frame(g);axes(g,70,28,900,298);
    const c=[colors.blue,colors.gold,colors.teal];
    totals.forEach((o,i)=>{
      o.vals.forEach((v,j)=>{
        if(v==null)return;const x=92+i*175+j*44,yy=326-v*298;
        const rect=svg("rect",{x,y:yy,width:36,height:326-yy,rx:3,fill:c[j]});
        rect.append(svg("title",{},protocols[j][0]+" "+(o.client===0?"Central":"C"+o.client)+" "+pct(v)));
        g.append(rect);
      });
      note(g,154+i*175,346,o.client===0?"Central":"C"+o.client,{"text-anchor":"middle","font-size":14});
    });
    const explain=$("protocolMeaning");
    explain.textContent="同一個 LEM2 計算程式、不同評估協定的條件性結果。官方 Test=28、原基準 Test=26、分組 Test=24，資料構成和 Train 量不同，不應把它們的差異直接稱為『重複模式造成的偏差量』。"+
      "三個數字保留在不同實驗系列，不能合併成 8,820 筆主矩陣。";
    $("protocolSource").textContent="官方檔來源：UCI 44 hayes-roth.test（獨立鏡像 SHA 2d8f77f...）｜補實驗 42 Seeds × 2 協定 × 5 架構 × 六策略 = 2,520 列。";
}
function activate(){
 for(const id of ["gDataset","gSplit","gSystem","gClient","gPolicy","gSeed"]){
    $(id)?.addEventListener("change",()=>{renderBest();renderTriage();renderProtocols();});
 }
 $("bestMetric")?.addEventListener("change",renderBest);
 $("protocolMetric")?.addEventListener("change",renderProtocols);
 $("bestJump")?.addEventListener("click",()=>document.querySelector("#bestTableWrap").scrollIntoView({behavior:"smooth"}));
}
async function load(){
 const pairs=[
  ["model_comparison.json",v=>ranking=v],
  ["conflict_triage_42.json",v=>triage=v],
  ["hayes_remediation.json",v=>hayes=v]
 ];
 const out=await Promise.allSettled(pairs.map(async([name,fn])=>{
   const r=await fetch("./data/"+name,{cache:"no-cache"});
   if(!r.ok)throw Error(name+" HTTP "+r.status);
   const x=await r.json();fn(x);return name;
 }));
 const errors=out.filter(r=>r.status==="rejected").map(r=>r.reason.message);
 if(errors.length)$("remediationHealth").textContent="部分新實驗來源未載入："+errors.join("；");
 else $("remediationHealth").textContent="三份新證據（42 Seeds 條件排名、7,560 組衝突判定、Hayes 2,520 組官方／分組實驗）均已載入";
 if(ranking)renderBest();
 if(triage)renderTriage();
 if(hayes)renderProtocols();
}
document.addEventListener("DOMContentLoaded",()=>{activate();load();});
})();
