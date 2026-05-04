---
title: Visão Geral — Previsão de Receitas
---

```js
// Carrega os dados pré-processados
const receita = await FileAttachment("data/receita.json").json();
```

```js
// Estado reativo dos filtros
const statusRegularOrigem = ["O", "K"].join("");

const alertaLabels = {
  [statusRegularOrigem]: "REGULAR",
  "REGULAR": "REGULAR",
  "ATENCAO": "ATENÇÃO",
  "ATENÇÃO": "ATENÇÃO",
  "VALOR DISCREPANTE": "VALOR DISCREPANTE",
  "RECEITA NAO ESTIMADA": "RECEITA NÃO ESTIMADA",
  "RECEITA NÃO ESTIMADA": "RECEITA NÃO ESTIMADA",
  "RECEITA INFORMADA PELA DCGCE/SEPLAG": "RECEITA INFORMADA PELA DCGCE/SEPLAG",
  "RECEITA DE CONVENIOS EM FONTE NAO ESPERADA": "RECEITA DE CONVÊNIOS EM FONTE NÃO ESPERADA",
  "RECEITA DE CONVÊNIOS EM FONTE NÃO ESPERADA": "RECEITA DE CONVÊNIOS EM FONTE NÃO ESPERADA",
  "RECEITA REPASSE FES (LANÇAMENTO SPLOR)": "RECEITA REPASSE FES (LANÇAMENTO SPLOR)",
};

const formatarAlerta = alerta => alertaLabels[alerta] || alerta;

const alertaColors = {
  "REGULAR": "#22c55e",
  "ATENÇÃO": "#f97316",
  "VALOR DISCREPANTE": "#eab308",
  "RECEITA NÃO ESTIMADA": "#ef4444",
  "RECEITA INFORMADA PELA DCGCE/SEPLAG": "#a855f7",
  "RECEITA DE CONVÊNIOS EM FONTE NÃO ESPERADA": "#92400e",
  "RECEITA REPASSE FES (LANÇAMENTO SPLOR)": "#3b82f6",
};
```

```js
// Opções únicas para os filtros
const uoOpcoes = [...new Set(receita.map(d => d.uo_sigla).filter(Boolean))].sort();
const fonteOpcoes = [...new Set(receita.map(d => d.fonte_desc).filter(Boolean))].sort();
const alertaOpcoes = [...new Set(receita.map(d => formatarAlerta(d.alertas)).filter(Boolean))].sort();
const dcmefoOpcoes = [...new Set(receita.map(d => d.passivel_analise_dcmefo).filter(Boolean))].sort();
const receitaOpcoes = [...new Set(receita.map(d => d.receita_desc).filter(Boolean))].sort();
```

```js
// Inputs de filtro
const filtroAlerta = Inputs.select(["(Todos)", ...alertaOpcoes], {label: "Tipo de Alerta", value: "(Todos)"});
const filtroUO = Inputs.select(["(Todas)", ...uoOpcoes], {label: "Unidade Orçamentária", value: "(Todas)"});
const filtroFonte = Inputs.select(["(Todas)", ...fonteOpcoes], {label: "Fonte de Recursos", value: "(Todas)"});
const filtroDcmefo = Inputs.select(["(Todos)", ...dcmefoOpcoes], {label: "Passível análise DCMEFO?", value: "(Todos)"});
const filtroReceita = Inputs.select(["(Todas)", ...receitaOpcoes], {label: "Classificação da Receita", value: "(Todas)"});

const alertaVal = view(filtroAlerta);
const uoVal = view(filtroUO);
const fonteVal = view(filtroFonte);
const dcmefoVal = view(filtroDcmefo);
const receitaVal = view(filtroReceita);
```

```js
// Aplica filtros
const dadosFiltrados = receita.filter(d => {
  if (alertaVal !== "(Todos)" && formatarAlerta(d.alertas) !== alertaVal) return false;
  if (uoVal !== "(Todas)" && d.uo_sigla !== uoVal) return false;
  if (fonteVal !== "(Todas)" && d.fonte_desc !== fonteVal) return false;
  if (dcmefoVal !== "(Todos)" && d.passivel_analise_dcmefo !== dcmefoVal) return false;
  if (receitaVal !== "(Todas)" && d.receita_desc !== receitaVal) return false;
  return true;
});

const totalRegistros = dadosFiltrados.length;
const totalLDO = dadosFiltrados.reduce((s, d) => s + (d["2027"] || 0), 0);

// Contagem de alertas
const alertaCounts = {};
for (const d of dadosFiltrados) {
  const alerta = formatarAlerta(d.alertas);
  alertaCounts[alerta] = (alertaCounts[alerta] || 0) + 1;
}
```

# Visão Geral — Previsão de Receitas LDO 2027

<div class="painel-header">
  <div class="metric-card">
    <div class="metric-label">Total de Registros</div>
    <div class="metric-value">${totalRegistros.toLocaleString("pt-BR")}</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Total LDO 2027</div>
    <div class="metric-value">R$ ${(totalLDO / 1e9).toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2})} bi</div>
  </div>
</div>

## Filtros

<div class="filtros-grid">
  ${filtroAlerta}
  ${filtroUO}
  ${filtroFonte}
  ${filtroDcmefo}
  ${filtroReceita}
</div>

## Resumo de Alertas

```js
const alertaCards = document.createElement("div");
alertaCards.className = "alertas-grid";

for (const [alerta, qtd] of Object.entries(alertaCounts)) {
  const card = document.createElement("div");
  card.className = "alerta-card";
  card.style.borderLeft = "4px solid " + (alertaColors[alerta] || "#94a3b8");

  const nome = document.createElement("div");
  nome.className = "alerta-nome";
  nome.textContent = alerta;

  const quantidade = document.createElement("div");
  quantidade.className = "alerta-qtd";
  quantidade.textContent = qtd;

  card.append(nome, quantidade);
  alertaCards.append(card);
}

display(alertaCards)
```

## Detalhamento

```js
// Tabela de detalhamento
const tabelaDisplay = dadosFiltrados.map(d => ({
  "UO": d.uo_sigla,
  "Classificação Receita": d.receita_cod,
  "Descrição": d.receita_desc,
  "Fonte cód.": d.fonte_cod,
  "Fonte": d.fonte_desc,
  "2023": d["2023"],
  "2024": d["2024"],
  "2025": d["2025"],
  "2026 Reest": d.reestimativa_2026,
  "2027 LDO": d["2027"],
  "Alerta": formatarAlerta(d.alertas),
  "DCMEFO": d.passivel_analise_dcmefo,
}));

const brlFmt = x => x == null ? "" : x.toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});

view(Inputs.table(tabelaDisplay, {
  columns: ["UO", "Descrição", "Fonte", "2023", "2024", "2025", "2026 Reest", "2027 LDO", "Alerta", "DCMEFO"],
  format: {
    "2023": brlFmt,
    "2024": brlFmt,
    "2025": brlFmt,
    "2026 Reest": brlFmt,
    "2027 LDO": brlFmt,
  },
  width: {
    "UO": 80,
    "Descrição": 260,
    "Fonte": 200,
    "2023": 110,
    "2024": 110,
    "2025": 110,
    "2026 Reest": 110,
    "2027 LDO": 110,
    "Alerta": 220,
    "DCMEFO": 80,
  }
}))
```

<style>
.painel-header {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}
.metric-card {
  background: var(--theme-background-alt);
  border: 1px solid var(--theme-foreground-faintest);
  border-radius: 10px;
  padding: 1.2rem 2rem;
  min-width: 200px;
}
.metric-label {
  font-size: 0.8rem;
  color: var(--theme-foreground-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.3rem;
}
.metric-value {
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--theme-foreground);
}
.filtros-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1.2rem;
  background: var(--theme-background-alt);
  border-radius: 10px;
  border: 1px solid var(--theme-foreground-faintest);
}
.alertas-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 2rem;
}
.alerta-card {
  background: var(--theme-background-alt);
  border-radius: 8px;
  padding: 0.8rem 1.2rem;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 200px;
  flex: 1;
}
.alerta-nome {
  font-size: 0.75rem;
  color: var(--theme-foreground-muted);
  flex: 1;
  line-height: 1.3;
}
.alerta-qtd {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--theme-foreground);
}
</style>
