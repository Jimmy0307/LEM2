/* Runs the upstream LEM2 Python modules, not a substitute JavaScript rule heuristic.
 * Only source code is fetched; uploaded CSV values stay in this worker.
 */
const PINNED_REF = "research/teacher-evidence-42-20261109";
const RAW_ROOT = "https://raw.githubusercontent.com/Jimmy0307/LEM2/"+PINNED_REF+"/roughset/";
const SOURCES = [
  "__init__.py","core.py","reduct.py","schema.py","adapters.py",
  "evaluation.py","research_evidence.py","federated.py","artifacts.py",
  "pipeline.py","preprocessing.py","splitting.py","environment.py",
  "paper.py","sources.py","app.py"
];
let pyodide = null;
let engineSource = null;
function update(message){self.postMessage({kind:"status",message});}
async function initialize(){
  if(pyodide) return;
  update("下載 Python WebAssembly 執行環境與 NumPy／pandas（第一次較慢）…");
  const mod = await import("https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.mjs");
  pyodide = await mod.loadPyodide({indexURL:"https://cdn.jsdelivr.net/pyodide/v0.27.7/full/"});
  await pyodide.loadPackage(["numpy","pandas"]);
  update("載入 GitHub 已驗證的原始 Rough Set／LEM2 模組…");
  const files=await Promise.all(SOURCES.map(async file=>{
    const response=await fetch(RAW_ROOT+file,{cache:"force-cache"});
    if(!response.ok)throw new Error("原始 Python 模組下載失敗："+file+"（HTTP "+response.status+"）");
    return {file,content:await response.text()};
  }));
  pyodide.FS.mkdirTree("/home/pyodide/roughset");
  for(const {file,content} of files){
    pyodide.FS.writeFile("/home/pyodide/roughset/"+file, content, {encoding:"utf8"});
  }
  await pyodide.runPythonAsync('import sys\nsys.path.insert(0,"/home/pyodide")');
  const bridge=await fetch("./runtime/engine.py",{cache:"no-cache"});
  if(!bridge.ok)throw new Error("engine.py 不可讀取，請用 HTTP 網站開啟，勿直接以 file:// 啟動。");
  engineSource=await bridge.text();
  update("原始模型已載入；開始計算 Reduct、LEM2 及六種策略…");
}
self.onmessage=async ({data})=>{
  if(data.kind!=="execute")return;
  try{
    await initialize();
    pyodide.globals.set("__USER_INPUT_JSON__",JSON.stringify(data.payload));
    await pyodide.runPythonAsync(engineSource);
    const value=pyodide.globals.get("__USER_RESULT_JSON__");
    const result=JSON.parse(value);
    self.postMessage({kind:"result",result});
  }catch(e){
    self.postMessage({kind:"error",message:String(e?.message||e),trace:String(e?.stack||"")});
  }
};
