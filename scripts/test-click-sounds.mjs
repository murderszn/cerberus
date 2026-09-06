import { test } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const source=fs.readFileSync(new URL('../assets/click-sounds.js',import.meta.url),'utf8');
function harness({stored=null,unsupported=false,storageBlocked=false}={}) {
  let created=0,played=0,clock=100;const listeners={},windowListeners={},saved={};
  const attrs={};const toggle={textContent:'',setAttribute:(k,v)=>attrs[k]=v,addEventListener:(type,fn)=>toggle[type]=fn};
  class Audio { constructor(){created++;this.state='running';this.currentTime=0;this.destination={};}createOscillator(){return {frequency:{setValueAtTime(){},exponentialRampToValueAtTime(){}},connect(){},disconnect(){},start(){played++;},stop(){}};}createGain(){return {gain:{setValueAtTime(){},exponentialRampToValueAtTime(){}},connect(){},disconnect(){}};} }
  const window={AudioContext:unsupported?undefined:Audio,addEventListener:(type,fn)=>windowListeners[type]=fn};
  vm.runInNewContext(source,{window,document:{querySelector:()=>toggle,addEventListener:(type,fn)=>listeners[type]=fn},localStorage:{getItem(){if(storageBlocked)throw Error();return stored;},setItem(k,v){if(storageBlocked)throw Error();saved[k]=v;}},performance:{now:()=>clock}});
  function fire(type,{trusted=true,detail=1,disabled=false,tagName='BUTTON',role=null,button=0,key='Enter',repeat=false,control=true}={}) {
    clock+=100;
    const node={disabled,tagName,getAttribute:(key)=>key==='role'?role:null,hasAttribute:()=>false,closest:()=>null};
    listeners[type]({isTrusted:trusted,detail,button,key,repeat,target:{closest:()=>control?node:null}});
  }
  return {fire,toggle,attrs,saved,windowListeners,get created(){return created;},get played(){return played;}};
}
test('no audio starts on load; a real primary control press produces one quiet click',()=>{
 const h=harness();assert.equal(h.created,0);assert.equal(h.toggle.textContent,'Sound on');h.fire('pointerdown');assert.equal(h.played,1);h.fire('click');assert.equal(h.played,1);
});
test('synthetic clicks, disabled controls, typing and secondary clicks stay silent',()=>{
 const h=harness();h.fire('pointerdown',{trusted:false});h.fire('pointerdown',{disabled:true});h.fire('pointerdown',{control:false});h.fire('pointerdown',{button:2});h.fire('click',{trusted:false,detail:0});h.fire('keydown',{tagName:'INPUT',key:'a'});assert.equal(h.created,0);
});
test('keyboard activation works for native and custom buttons',()=>{
 const h=harness();h.fire('click',{detail:0});h.fire('keydown',{tagName:'DIV',role:'button'});h.fire('keydown',{tagName:'DIV',role:'button',repeat:true});assert.equal(h.played,2);
});
test('mute persists, prevents playback, and restores across a fresh page',()=>{
 const h=harness();h.toggle.click({isTrusted:true});assert.equal(h.attrs['aria-pressed'],'false');assert.equal(h.saved['cerberus:sound-enabled'],'false');h.fire('pointerdown');assert.equal(h.played,0);
 const next=harness({stored:h.saved['cerberus:sound-enabled']});next.fire('pointerdown');assert.equal(next.played,0);next.toggle.click({isTrusted:true});assert.equal(next.attrs['aria-pressed'],'true');assert.equal(next.played,1);
});
test('storage restrictions and missing AudioContext never break controls',()=>{
 const h=harness({unsupported:true,storageBlocked:true});h.fire('pointerdown');h.toggle.click({isTrusted:true});assert.equal(h.created,0);assert.equal(h.toggle.textContent,'Sound off');
});
test('mute synchronizes with another tab',()=>{
 const h=harness();h.windowListeners.storage({key:'cerberus:sound-enabled',newValue:'false'});h.fire('pointerdown');assert.equal(h.played,0);assert.equal(h.toggle.textContent,'Sound off');
});
