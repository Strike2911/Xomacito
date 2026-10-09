const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class File {
  constructor(name, text='') { this.name=name; this.text=text; this.isFile=true; }
  async read() { return this.text; }
  async write(value) { this.text=value; }
}
class Folder {
  constructor() { this.files=new Map(); }
  async getEntry(name) { if (!this.files.has(name)) throw Error('missing'); return this.files.get(name); }
  async createFile(name) { const file=new File(name);this.files.set(name,file);return file; }
  async createFolder(name) { const folder=new Folder();this.files.set(name,folder);return folder; }
  async getEntries() { return [...this.files.values()]; }
}
const context=vm.createContext({ require: () => ({storage:{localFileSystem:{}},entrypoints:{setup(){}}}),
  localStorage:{getItem(){return null;}}, setInterval(){return 1;}, clearInterval(){}, console });
vm.runInContext(fs.readFileSync('premiere-panel/index.js','utf8') + `
  globalThis.test = { processBridge, libraryItems, pathKey, automaticTimelineFor,
    autoOptions(enabled, images=false){ autoTimeline=enabled; timelineImages=images; },
    setFolder(value){ libraryFolder=value; },
    setProject(value){ activeProject=async()=>value; },
    replaceImport(fn){ ensureImported=fn; }, replaceInsert(fn){ insertBridgeItem=fn; } };
  setStatus=()=>{};
  renderConnection=()=>{}; renderSelection=()=>{}; renderItems=()=>{};
  projectMediaIndex=async()=>new Map();
`, context);
(async()=>{
  const root=new Folder();const bridge=await root.createFolder('.xomacito-link');
  context.test.setFolder(root);context.test.setProject({name:'Prueba',guid:'project-a',getActiveSequence:async()=>({}),getRootItem:async()=>({})});
  let imports=0,inserts=0;context.test.replaceImport(async()=>{imports++;return {};});context.test.replaceInsert(async()=>{inserts++;});
  const id='a'.repeat(32);
  function request(key, extras={}) { bridge.files.set(`${key}.request.json`,new File(`${key}.request.json`,JSON.stringify({schema:1,id:key,path:'C:/Media/Prueba con espacios.mp4',action:'timeline',expires:Date.now()/1000+120,project:'Prueba',...extras}))); }
  request(id);await context.test.processBridge();await context.test.processBridge();
  assert.equal(imports,1);assert.equal(inserts,1);assert.equal(JSON.parse(await (await bridge.getEntry(`${id}.result.json`)).read()).ok,true);
  bridge.files.delete(`${id}.result.json`);await context.test.processBridge();assert.equal(inserts,1,'A restarted panel must not insert an already claimed request again');
  const expired='b'.repeat(32);request(expired,{expires:0});await context.test.processBridge();assert.equal(imports,1);
  const wrong='c'.repeat(32);request(wrong,{project:'Otro'});await context.test.processBridge();assert.equal(imports,1);
  const invalid='d'.repeat(32);request(invalid,{path:'C:/script.exe'});await context.test.processBridge();assert.equal(imports,1);
  const normal='e'.repeat(32);request(normal,{action:'import'});await context.test.processBridge();assert.equal(imports,2);assert.equal(inserts,1);
  const external='D:/Material externo/audio.wav';
  root.files.set('.xomacito-library.json',new File('.xomacito-library.json',JSON.stringify({schema:1,items:[{path:external,name:'audio.wav'},{path:external,name:'repetido.wav'},{path:'D:/script.exe'}]})));
  const linked=await context.test.libraryItems(root);assert.equal(linked.length,1);assert.equal(linked[0].path,external);
  assert.equal(context.test.pathKey('C:\\Media\\Prueba.mp4'),context.test.pathKey('c:/media/prueba.mp4'));
  assert.notEqual(context.test.pathKey('/Volumes/Media/A.mp4'),context.test.pathKey('/Volumes/Media/a.mp4'));
  context.test.autoOptions(true);
  assert.equal(context.test.automaticTimelineFor({automatic:true},['C:/media/clip.mp4']),true);
  assert.equal(context.test.automaticTimelineFor({automatic:true},['C:/media/poster.png']),false);
  assert.equal(context.test.automaticTimelineFor({automatic:false},['C:/media/clip.mp4']),false);
  assert.equal(context.test.automaticTimelineFor({automatic:true},['C:/media/a.mp4','C:/media/b.mp4']),false);
  context.test.autoOptions(true,true);
  assert.equal(context.test.automaticTimelineFor({automatic:true},['C:/media/poster.png']),true);
  context.test.autoOptions(false);
  const batch='f'.repeat(32);request(batch,{schema:2,action:'import',paths:['C:/Media/one.mp4','c:/media/ONE.mp4','D:/Audio/two.wav'],projectId:'project-a'});
  await context.test.processBridge();assert.equal(imports,4,'Batch paths are deduplicated');
  const switched='1'.repeat(32);request(switched,{projectId:'project-b'});
  await context.test.processBridge();assert.equal(imports,4,'Same name, different project GUID must be rejected');
  const noSequence='2'.repeat(32);request(noSequence);
  context.test.setProject({name:'Prueba',guid:'project-a',getActiveSequence:async()=>null});
  await context.test.processBridge();assert.equal(imports,4,'Missing sequence must be rejected before import');
  const auto='3'.repeat(32);request(auto,{automatic:true,action:'import'});
  await context.test.processBridge();assert.equal(imports,4,'Disabled autoimport must reject queued automatic requests');
  const traversal='4'.repeat(32);request(traversal,{path:'../movie.mp4',action:'import'});
  await context.test.processBridge();assert.equal(imports,4,'Relative paths cannot enter bridge');
  context.test.setProject(null);
  await context.test.processBridge();
  assert.equal(JSON.parse(await (await bridge.getEntry('heartbeat.json')).read()).project,'');
  console.log('Premiere bridge: import, timeline, acknowledgement, replay, expiry and project checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
