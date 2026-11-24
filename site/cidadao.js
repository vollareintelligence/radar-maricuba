/* Lupa Maricá — Cidadão Fiscalizador (PC + Mobile) */
(function () {
  const CFG = window.LUPA_CIDADAO_CFG || {};
  const SB_URL = (CFG.SUPABASE_URL || '').replace(/\/+$/, '');
  const SB_KEY = CFG.SUPABASE_ANON_KEY || '';
  const READY = Boolean(SB_URL && SB_KEY);

  const $ = s => document.querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmtDate = iso => {
    try { return new Date(iso).toLocaleDateString('pt-BR'); } catch { return ''; }
  };

  const form = $('#cfForm');
  const boxFeed = $('#cfFeed');
  if (!form || !boxFeed) return;

  const stLabels = {
    aprovado: 'Aguardando solução',
    andamento: 'Em andamento',
    resolvido: 'Resolvido'
  };

  let fotoBlob = null;
  let latVal = null;
  let lngVal = null;
  let allRows = [];
  let stFilter = 'todos';

  // Toggle campos privados quando anônimo estiver desmarcado
  const chkAnon = $('#cfAnon');
  const privWrap = $('#cfPrivWrap');
  function syncAnon() {
    if (!chkAnon || !privWrap) return;
    privWrap.hidden = chkAnon.checked;
  }
  if (chkAnon) {
    chkAnon.addEventListener('change', syncAnon);
    syncAnon();
  }

  // Compressão no navegador + remoção automática de metadados EXIF via <canvas>
  function comprimirFoto(file) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => {
        URL.revokeObjectURL(url);
        const maxDim = 1280;
        let w = img.naturalWidth || img.width;
        let h = img.naturalHeight || img.height;
        if (w > maxDim || h > maxDim) {
          if (w >= h) { h = Math.round(h * maxDim / w); w = maxDim; }
          else { w = Math.round(w * maxDim / h); h = maxDim; }
        }
        const cv = document.createElement('canvas');
        cv.width = w;
        cv.height = h;
        const ctx = cv.getContext('2d');
        ctx.drawImage(img, 0, 0, w, h);
        cv.toBlob(b => {
          if (b) resolve(b);
          else reject(new Error('Não foi possível processar a imagem.'));
        }, 'image/jpeg', 0.82);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error('Arquivo de imagem inválido.'));
      };
      img.src = url;
    });
  }

  const inputCam = $('#cfCam');
  const inputFoto = $('#cfFoto');
  const prevWrap = $('#cfPreview');

  async function onPickFile(inputEl) {
    const f = inputEl && inputEl.files && inputEl.files[0];
    if (!f) return;
    fotoBlob = null;
    try {
      fotoBlob = await comprimirFoto(f);
      const kb = Math.round(fotoBlob.size / 1024);
      const pUrl = URL.createObjectURL(fotoBlob);
      prevWrap.innerHTML = `<img src="${pUrl}" alt="Prévia da foto selecionada"><span>Foto pronta (${kb} KB · metadados EXIF removidos)</span><button type="button" class="btn" id="cfRmFoto" style="margin-left:auto;min-height:36px;padding:4px 10px;font-size:13px">Remover</button>`;
      prevWrap.hidden = false;
      const rm = $('#cfRmFoto');
      if (rm) rm.addEventListener('click', () => {
        fotoBlob = null;
        if (inputCam) inputCam.value = '';
        if (inputFoto) inputFoto.value = '';
        prevWrap.hidden = true;
        prevWrap.innerHTML = '';
      });
    } catch (err) {
      prevWrap.innerHTML = `<span>${esc(err.message)}</span>`;
      prevWrap.hidden = false;
    }
  }
  if (inputCam) inputCam.addEventListener('change', () => onPickFile(inputCam));
  if (inputFoto) inputFoto.addEventListener('change', () => onPickFile(inputFoto));

  // Botão opcional de GPS (útil no celular)
  const btnGps = $('#cfGps');
  const gpsInfo = $('#cfGpsInfo');
  if (btnGps) {
    btnGps.addEventListener('click', () => {
      if (!navigator.geolocation) {
        gpsInfo.textContent = 'Seu navegador não suporta localização automática. Basta digitar a rua e o bairro.';
        return;
      }
      btnGps.disabled = true;
      gpsInfo.textContent = 'Obtendo localização...';
      navigator.geolocation.getCurrentPosition(
        pos => {
          latVal = Number(pos.coords.latitude.toFixed(6));
          lngVal = Number(pos.coords.longitude.toFixed(6));
          gpsInfo.textContent = `Localização anexada (${latVal}, ${lngVal}).`;
          btnGps.disabled = false;
        },
        () => {
          gpsInfo.textContent = 'Não foi possível capturar o GPS. Sem problema: informe o bairro e a rua acima.';
          btnGps.disabled = false;
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });
  }

  function setMsg(txt, type) {
    const m = $('#cfMsg');
    m.innerHTML = txt;
    m.className = 'cf-msg ' + (type || '');
    m.hidden = false;
  }

  async function uploadFoto(blob) {
    const rand = Math.random().toString(36).slice(2, 10);
    const path = `${Date.now()}-${rand}.jpg`;
    const r = await fetch(`${SB_URL}/storage/v1/object/fotos-relatos/${path}`, {
      method: 'POST',
      headers: {
        'apikey': SB_KEY,
        'Authorization': 'Bearer ' + SB_KEY,
        'Content-Type': 'image/jpeg',
        'x-upsert': 'false'
      },
      body: blob
    });
    if (!r.ok) throw new Error('Falha ao enviar a foto. Tente novamente.');
    return `${SB_URL}/storage/v1/object/public/fotos-relatos/${path}`;
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();
    // Honeypot anti-spam
    const hp = $('#cfWebsite');
    if (hp && hp.value.trim()) {
      setMsg('Relato recebido para conferência.', 'ok');
      form.reset();
      return;
    }

    if (!READY) {
      setMsg('O canal <b>Cidadão Fiscalizador</b> está em ativação final. Em breve você poderá enviar seus relatos diretamente por aqui.', 'warn');
      return;
    }

    const btn = $('#cfSubmit');
    btn.disabled = true;
    btn.textContent = 'Enviando...';
    $('#cfMsg').hidden = true;

    try {
      let foto_url = null;
      if (fotoBlob) {
        foto_url = await uploadFoto(fotoBlob);
      }
      const anonimo = chkAnon ? chkAnon.checked : true;
      const payload = {
        p_categoria: $('#cfCat').value,
        p_titulo: $('#cfTitulo').value.trim(),
        p_bairro: $('#cfBairro').value.trim(),
        p_local_referencia: $('#cfLocal').value.trim(),
        p_descricao: $('#cfDesc').value.trim(),
        p_lat: latVal,
        p_lng: lngVal,
        p_foto_url: foto_url,
        p_anonimo: anonimo,
        p_nome_denunciante: anonimo ? null : ($('#cfNome').value.trim() || null),
        p_contato_denunciante: anonimo ? null : ($('#cfZap').value.trim() || null)
      };

      const r = await fetch(`${SB_URL}/rest/v1/rpc/enviar_relato`, {
        method: 'POST',
        headers: {
          'apikey': SB_KEY,
          'Authorization': 'Bearer ' + SB_KEY,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      const data = await r.json();
      if (!r.ok) throw new Error((data && (data.message || data.hint)) || 'Não foi possível enviar o relato.');

      const proto = data && data.protocolo ? `#${esc(data.protocolo)}` : 'registrado';
      setMsg(`<b>Relato ${proto} enviado com sucesso!</b> Ele já está na fila de conferência da Lupa Maricá e será publicado após verificação (seus dados pessoais nunca aparecem no site).`, 'ok');
      form.reset();
      fotoBlob = null;
      latVal = null;
      lngVal = null;
      prevWrap.hidden = true;
      prevWrap.innerHTML = '';
      if (gpsInfo) gpsInfo.textContent = '';
      syncAnon();
    } catch (err) {
      setMsg(esc(err.message || 'Erro ao enviar. Tente novamente.'), 'err');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Enviar relato para conferência';
    }
  });

  // Vitrine pública de relatos aprovados
  function renderFeed() {
    const q = ($('#cfBusca') && $('#cfBusca').value || '').trim().toLowerCase();
    const list = allRows.filter(r => {
      if (stFilter !== 'todos' && r.status !== stFilter) return false;
      if (!q) return true;
      return `${r.protocolo} ${r.titulo} ${r.categoria} ${r.bairro} ${r.local_referencia} ${r.descricao}`.toLowerCase().includes(q);
    });

    if (!list.length) {
      boxFeed.innerHTML = '<div class="card"><p class="note" style="margin:0">Nenhum relato público encontrado para esse filtro ainda. Seja o primeiro morador a enviar um problema da sua rua ou bairro.</p></div>';
      return;
    }

    boxFeed.innerHTML = `<div class="cf-grid">${list.map(r => `
      <article class="cf-card">
        <div class="cf-card-head">
          <span class="cf-proto">#${esc(r.protocolo)}</span>
          <span class="cf-st cf-st-${esc(r.status)}">${esc(stLabels[r.status] || r.status)}</span>
        </div>
        ${r.foto_url ? `<a class="cf-imgwrap" href="${esc(r.foto_url)}" target="_blank" rel="noopener"><img src="${esc(r.foto_url)}" alt="Foto do problema ${esc(r.protocolo)} em ${esc(r.bairro)}" loading="lazy"></a>` : ''}
        <div class="cf-card-body">
          <div class="cf-meta">${esc(r.categoria)} · ${esc(fmtDate(r.created_at))}</div>
          <h3>${esc(r.titulo)}</h3>
          <p class="cf-loc"><b>${esc(r.bairro)}</b> — ${esc(r.local_referencia)}</p>
          <p class="cf-desc">${esc(r.descricao)}</p>
          ${r.resposta_prefeitura ? `<div class="cf-resp"><b>Resposta da Prefeitura:</b> ${esc(r.resposta_prefeitura)}</div>` : ''}
          ${r.atuacao_vereador ? `<div class="cf-resp cf-resp-ver"><b>Acompanhamento / Câmara:</b> ${esc(r.atuacao_vereador)}</div>` : ''}
        </div>
      </article>
    `).join('')}</div>`;
  }

  const tabs = $('#cfTabs');
  if (tabs) {
    tabs.addEventListener('click', e => {
      const b = e.target.closest('button[data-cfst]');
      if (!b) return;
      stFilter = b.dataset.cfst;
      tabs.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
      renderFeed();
    });
  }
  const busca = $('#cfBusca');
  if (busca) busca.addEventListener('input', renderFeed);

  async function carregarFeed() {
    if (!READY) {
      boxFeed.innerHTML = '<div class="card"><p class="note" style="margin:0">Os relatos verificados pela equipe da Lupa Maricá aparecerão aqui com número de protocolo (<code>#LM-XXXX</code>), foto do local e espaço para resposta da Prefeitura ou atuação de vereadores.</p></div>';
      return;
    }
    try {
      const r = await fetch(
        `${SB_URL}/rest/v1/relatos?select=id,protocolo,created_at,categoria,titulo,bairro,local_referencia,descricao,foto_url,status,resposta_prefeitura,atuacao_vereador&status=in.(aprovado,andamento,resolvido)&order=created_at.desc&limit=60`,
        { headers: { 'apikey': SB_KEY, 'Authorization': 'Bearer ' + SB_KEY } }
      );
      if (!r.ok) throw new Error();
      allRows = await r.json();
      renderFeed();
    } catch {
      boxFeed.innerHTML = '<div class="card"><p class="note" style="margin:0">Não foi possível carregar os relatos públicos no momento.</p></div>';
    }
  }

  carregarFeed();
})();
