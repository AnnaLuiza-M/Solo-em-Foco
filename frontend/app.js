/* Solo em Foco: CE/PST/pH consultados do backend; nada de dados fictícios na interface. */
'use strict';
const porId = id => document.getElementById(id);
const fmt = (n, d=2) => Number.isFinite(n) ? n.toLocaleString('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d}) : '—';
const request = async path => {
  const res=await fetch(path);
  if(!res.ok){let msg=`Erro HTTP ${res.status}`;try{msg=(await res.json()).detail||msg}catch{}throw new Error(msg)}
  return res.json();
};
const atualizarStatus=text=>{porId('status').textContent=text};
const el=(tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node};
let mapa=null,marcador=null,cities=[],analise=null,scatterData=[];

function showTab(name){
  const chosen = name==='analise'?'analise':'consulta';
  for(const part of ['consulta','analise']){
    const selected=part===chosen;
    porId('tab'+part[0].toUpperCase()+part.slice(1)).hidden=!selected;
    porId('nav'+part[0].toUpperCase()+part.slice(1)).classList.toggle('active',selected);
    porId('nav'+part[0].toUpperCase()+part.slice(1)).setAttribute('aria-selected',String(selected));
  }
  window.scrollTo({top:0,behavior:'smooth'});
  if(chosen==='consulta' && mapa)setTimeout(()=>mapa.invalidateSize(),50);
  if(chosen==='analise')drawScatter();
}

function exibirRelacoesConjuntas(relations){
  const root=porId('relacoesConjuntas');root.replaceChildren();
  for(const [i,data] of (relations||[]).entries()){
    const card=el('article','joint-card');card.append(el('span','step',String(i+1)));
    card.append(el('h3','',data.titulo));
    card.append(el('span','small-label','O QUE O MAPA MOSTRA'));
    card.append(el('p','',data.leitura));
    const why=el('div','context');why.append(el('span','small-label','POR QUE IMPORTA'));
    why.append(el('p','',data.importancia));card.append(why);root.append(card);
  }
}

function exibirComparacaoEstadual(data){
  const root=porId('comparacaoEstadual');root.replaceChildren();
  const settings=[['ce','CE · sais solúveis','dS/m',3],['pst','PST · sódio trocável','%',3],['ph','pH · acidez / alcalinidade','',2]];
  for(const [key,title,unit,decimals] of settings){
    const val=data?.[key];if(!val)continue;
    const card=el('article','state-card');
    card.append(el('h3','',title));
    card.append(el('div','relative',val.posicao));
    // Faixa visual de categorias (não é um percentil numérico do ponto consultado).
    const line=el('div','state-line');line.setAttribute('aria-label',`Faixa: ${val.posicao}`);
    const dot=el('span','dot');
    dot.style.left=val.faixa==='abaixo_mediana'?'22%':val.faixa==='entre_mediana_p95'?'68%':'97%';
    line.append(dot);card.append(line);
    const labels=el('div','state-labels');
    labels.append(el('span','','Abaixo mediana'),el('span','','Até P95'),el('span','','Acima P95'));
    card.append(labels);
    card.append(el('p','state-nums',`Seu ponto: ${fmt(val.valor,decimals)} ${unit} · Mediana: ${fmt(val.mediana,decimals)} ${unit} · P95: ${fmt(val.p95,decimals)} ${unit}`));
    card.append(el('p','',val.explicacao));root.append(card);
  }
}

function limparResultado(mensagem) {
  porId('tituloConsulta').textContent = 'Consulta não concluída';
  porId('nomeMunicipio').textContent = 'Sem resultado';
  porId('introducaoConsulta').textContent = mensagem;
  porId('leituraInicial').textContent = 'Selecione outro ponto dentro da Bahia.';
  porId('quadroOrientacao').hidden = true;

  if (marcador) {
    marcador.remove();
    marcador = null;
  }

  for (const id of ['valorCe', 'valorPst', 'valorPh']) {
    porId(id).textContent = '—';
  }
  porId('relacoesConjuntas').replaceChildren(
    el('p', 'secondary', 'Nenhuma interpretação disponível: consulte um ponto válido.')
  );
  porId('comparacaoEstadual').replaceChildren(
    el('div', 'panel muted-placeholder', 'Nenhuma comparação disponível.')
  );
  atualizarStatus(mensagem);
}

async function consultarSolo(latitude, longitude) {
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    limparResultado('Informe latitude e longitude numéricas válidas.');
    return;
  }

  atualizarStatus('Consultando CE, PST e pH dos mapas...');
  try {
    const dados = await request(`/api/consulta?lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}`);
    const { estimativas, interpretacao, localizacao } = dados;
    const municipio = localizacao.municipio;

    porId('nomeMunicipio').textContent = municipio;
    porId('tituloConsulta').textContent = `Resultado em ${municipio}`;
    porId('introducaoConsulta').textContent = 'Estimativas do pixel correspondente à localização no mapa da Embrapa.';
    porId('valorCe').textContent = fmt(estimativas.ce, 3);
    porId('valorPst').textContent = fmt(estimativas.pst, 3);
    porId('valorPh').textContent = fmt(estimativas.ph, 2);
    porId('leituraInicial').textContent = `${interpretacao.titulo}. ${interpretacao.explicacao}`;
    porId('orientacaoConsulta').textContent = interpretacao.sugestao;
    porId('notaConsulta').textContent = interpretacao.nota;
    porId('quadroOrientacao').hidden = false;
    exibirRelacoesConjuntas(interpretacao.relacoes_conjuntas);
    exibirComparacaoEstadual(interpretacao.comparacao_bahia);

    porId('lat').value = latitude.toFixed(6);
    porId('lon').value = longitude.toFixed(6);
    if (mapa) {
      if (marcador) marcador.remove();
      marcador = L.marker([latitude, longitude]).addTo(mapa);
      mapa.setView([latitude, longitude], 10);
    }
    atualizarStatus(`Consulta concluída: ${municipio} — comparação com os 417 municípios da Bahia.`);
  } catch (erro) {
    limparResultado(erro.message);
  }
}

function bars(id,rows,key,unit=''){
  const root=porId(id);root.replaceChildren();if(!rows?.length)return root.append(el('p','secondary','Sem dados.'));
  const max=Math.max(...rows.map(r=>r[key]),0.001);
  rows.forEach(r=>{
    const row=el('div','barrow');const label=el('span','name',r.municipio);label.title=r.municipio;
    const track=el('div','track'),fill=el('div','fill');fill.style.width=`${100*r[key]/max}%`;
    track.append(fill);row.append(label,track,el('strong','',fmt(r[key],2)+unit));root.append(row);
  });
}

const pairs={
  ce_pst:{x:'ce_mediana',y:'pst_mediana',labelX:'CE mediana (dS/m)',labelY:'PST mediana (%)',corr:['ce_mediana','pst_mediana']},
  ce_ph:{x:'ce_mediana',y:'ph_mediana',labelX:'CE mediana (dS/m)',labelY:'pH mediano',corr:['ce_mediana','ph_mediana']},
  pst_ph:{x:'pst_mediana',y:'ph_mediana',labelX:'PST mediana (%)',labelY:'pH mediano',corr:['pst_mediana','ph_mediana']}
};
const SVGNS='http://www.w3.org/2000/svg';
function svg(tag,attrs={},text){const n=document.createElementNS(SVGNS,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,String(v)));if(text!==undefined)n.textContent=text;return n}
function drawScatter(){
  const root=porId('scatterPlot');root.replaceChildren();
  if(!scatterData.length||!analise){root.append(svg('text',{x:25,y:40},'Carregando dados...'));return}
  const spec=pairs[porId('scatterPair').value]||pairs.ce_pst;
  const width=760,height=360,left=88,right=24,top=24,bottom=68;
  const plotW=width-left-right,plotH=height-top-bottom;
  // log1p é explicitado na interface, para não confundir a escala.
  const tr=(v,key)=>key.startsWith('ph_')?v:Math.log1p(Math.max(0,v));
  const inv=(v,key)=>key.startsWith('ph_')?v:Math.expm1(v);
  const rows=scatterData.filter(v=>Number.isFinite(v[spec.x])&&Number.isFinite(v[spec.y]));
  const xx=rows.map(v=>tr(v[spec.x],spec.x)),yy=rows.map(v=>tr(v[spec.y],spec.y));
  let xmin=Math.min(...xx),xmax=Math.max(...xx),ymin=Math.min(...yy),ymax=Math.max(...yy);
  if(xmax===xmin)xmax=xmin+1;if(ymax===ymin)ymax=ymin+1;
  const xVal=v=>left+(tr(v,spec.x)-xmin)/(xmax-xmin)*plotW;
  const yVal=v=>top+plotH-(tr(v,spec.y)-ymin)/(ymax-ymin)*plotH;
  root.append(svg('rect',{x:0,y:0,width,height,fill:'#fcfdfb'}));
  for(let i=0;i<=4;i++){
    const k=i/4,x=left+k*plotW,y=top+(1-k)*plotH;
    root.append(svg('line',{x1:left,y1:y,x2:left+plotW,y2:y,stroke:'#dfe9de','stroke-width':1}));
    root.append(svg('line',{x1:x,y1:top,x2:x,y2:top+plotH,stroke:'#e8eee6','stroke-width':1}));
    root.append(svg('text',{x:left-10,y:y+4,fill:'#5b7465','font-size':11,'text-anchor':'end'},fmt(inv(ymin+k*(ymax-ymin),spec.y),2)));
    root.append(svg('text',{x,y:top+plotH+21,fill:'#5b7465','font-size':11,'text-anchor':'middle'},fmt(inv(xmin+k*(xmax-xmin),spec.x),2)));
  }
  root.append(svg('line',{x1:left,y1:top,x2:left,y2:top+plotH,stroke:'#7d9884','stroke-width':1.5}));
  root.append(svg('line',{x1:left,y1:top+plotH,x2:left+plotW,y2:top+plotH,stroke:'#7d9884','stroke-width':1.5}));
  for(const v of rows){
    const c=svg('circle',{cx:xVal(v[spec.x]),cy:yVal(v[spec.y]),r:3.7,fill:'#378360',opacity:0.43});
    c.append(svg('title',{},`${v.municipio}: ${spec.labelX} ${fmt(v[spec.x],3)}; ${spec.labelY} ${fmt(v[spec.y],3)}`));
    root.append(c);
  }
  root.append(svg('text',{x:left+plotW/2,y:height-10,'text-anchor':'middle','font-size':14,'font-weight':650,fill:'#214b3c'},spec.labelX));
  root.append(svg('text',{x:15,y:top+plotH/2,'text-anchor':'middle','font-size':13,'font-weight':650,fill:'#214b3c',transform:`rotate(-90,15,${top+plotH/2})`},spec.labelY));
  const corr=analise.correlacoes_spearman_medianas_municipais[spec.corr[0]][spec.corr[1]];
  porId('corrSelected').textContent=`Spearman: ${fmt(corr,3)}`;
  const force=Math.abs(corr)>=.7?'associação forte':Math.abs(corr)>=.4?'associação moderada':'associação fraca';
  porId('corrExplanation').textContent=`Os municípios apresentam ${force} ${corr>=0?'positiva':'negativa'} entre essas medianas estimadas. Isso não implica causalidade.`;
}

async function load(){
  try{
    const [meta,a,list,scatter]=await Promise.all([
      request('/api/metadados'),request('/api/analise'),request('/api/municipios?limite=417'),request('/api/analise/dispersao')
    ]);
    cities=list;analise=a;scatterData=scatter.pontos;
    porId('qMunicipios').textContent=meta.total_municipios;
    porId('p95ce').textContent=fmt(meta.percentil95_referencia.ce,3);
    porId('p95pst').textContent=fmt(meta.percentil95_referencia.pst,3);
    const c=a.correlacoes_spearman_medianas_municipais;
    porId('corrCePst').textContent=fmt(c.ce_mediana.pst_mediana,3);
    porId('corrCePh').textContent=fmt(c.ce_mediana.ph_mediana,3);
    porId('corrPstPh').textContent=fmt(c.pst_mediana.ph_mediana,3);
    bars('rankingCE',a.top_ce_mediana,'ce_mediana');bars('rankingAmbos',a.top_coincidencia,'coincidencia_pct','%');
    for(const id of ['cityA','cityB']){
      const s=porId(id);s.replaceChildren();cities.forEach(city=>{const opt=document.createElement('option');opt.value=city.codigo_ibge;opt.textContent=city.municipio;s.append(opt)});
    }
    porId('cityA').value='2918407';porId('cityB').value='2907202';
    atualizarStatus(`Base carregada: ${meta.total_municipios} municípios e ${meta.total_pixels_validos.toLocaleString('pt-BR')} pixels válidos.`);
    drawScatter();await compare();
  }catch(err){atualizarStatus('Falha ao carregar análise de dados: '+err.message)}
}

async function compare(){
  try{
    const code1=porId('cityA').value,code2=porId('cityB').value;if(!code1||!code2)return;
    const x=await request(`/api/comparar?codigo1=${encodeURIComponent(code1)}&codigo2=${encodeURIComponent(code2)}`);
    const labels=[['CE mediana (dS/m)','ce_mediana',3],['PST mediana (%)','pst_mediana',3],['pH mediano','ph_mediana',2],['Pixels acima P95 estadual CE (%)','ce_acima_p95_pct',2],['Pixels acima P95 estadual PST (%)','pst_acima_p95_pct',2],['Coincidência CE/PST acima P95 (%)','coincidencia_pct',2]];
    const root=porId('comparison');const table=el('table'),head=el('thead'),tr=el('tr');
    for(const name of ['Indicador',x.regiao_a.municipio,x.regiao_b.municipio])tr.append(el('th','',name));head.append(tr);table.append(head);
    const body=el('tbody');for(const [label,key,dec] of labels){const row=el('tr');for(const v of [label,fmt(x.regiao_a[key],dec),fmt(x.regiao_b[key],dec)])row.append(el('td','',v));body.append(row)}table.append(body);
    root.replaceChildren(table,el('p','secondary',x.nota));
  }catch(err){porId('comparison').textContent=err.message}
}

function iniciarMapa(){
  if(typeof L==='undefined'){porId('map').textContent='Mapa indisponível sem acesso à biblioteca Leaflet. Você pode consultar pelas coordenadas acima.';return}
  mapa=L.map('map',{scrollWheelZoom:false}).setView([-12.5,-41.1],7);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:18}).addTo(mapa);
  fetch('/api/municipios/geojson').then(res=>res.json()).then(geo=>{
    const layer=L.geoJSON(geo,{style:{color:'#448260',weight:.5,fillColor:'#9ac8a4',fillOpacity:.16},onEachFeature:(feat,layer)=>layer.bindTooltip(feat.properties.municipio)}).addTo(mapa);
    mapa.fitBounds(layer.getBounds());
  }).catch(()=>{});
  mapa.on('click',e=>consultarSolo(e.latlng.lat,e.latlng.lng));
}

for(const button of document.querySelectorAll('[data-tab]'))button.addEventListener('click',()=>showTab(button.dataset.tab));
porId('botaoConsultar').addEventListener('click',()=>{
  const a=porId('lat').value.trim(),b=porId('lon').value.trim();
  if(!a||!b)return limparResultado('Preencha latitude e longitude.');
  consultarSolo(Number(a),Number(b));
});
porId('botaoExemplo').addEventListener('click',()=>consultarSolo(-9.513883,-40.307956));
porId('botaoLocalizacao').addEventListener('click',()=>{
  if(!navigator.geolocation)return limparResultado('GPS não disponível. Informe as coordenadas.');
  atualizarStatus('Solicitando permissão para acessar a localização...');
  navigator.geolocation.getCurrentPosition(p=>consultarSolo(p.coords.latitude,p.coords.longitude),e=>atualizarStatus('Não foi possível obter a localização: '+e.message),{enableHighAccuracy:false,timeout:12000});
});
porId('scatterPair').addEventListener('change',drawScatter);
porId('compareBtn').addEventListener('click',compare);
iniciarMapa();load();
