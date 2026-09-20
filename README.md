# Metragen para Home Assistant

[![CI](https://github.com/roquerodrigo/ha-metragen/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-metragen/actions/workflows/ci.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

[![Abra a sua instância do Home Assistant e o repositório dentro do HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-metragen&category=integration)

---

Integração custom do [Home Assistant](https://www.home-assistant.io/) para o
portal do morador do [Sistema Metragen](https://www.sistemametragen.com.br/metragen),
o serviço de medição individualizada de água e gás usado por condomínios
brasileiros. Ela entra com as mesmas credenciais que você usa no portal e
transforma cada medidor listado no seu apartamento em um dispositivo com as
respectivas leituras.

## Entidades

É criado um dispositivo por medidor que o portal lista, nomeado pelo código do
medidor e pelo que ele mede — "AF1234 Água Fria", "AQ1234 Água Quente",
"AQ1234 Gás" —, cada um com quatro sensores:

| Sensor | Unidade | Classe | O que informa |
|---|---|---|---|
| Leitura | m³ | water / gas, `total_increasing` | Valor do contador na última leitura publicada. Use como fonte de água ou gás no painel de Energia. |
| Consumo Mensal | m³ | water / gas, `total` | Volume cobrado no período da última leitura; `last_reset` é o primeiro dia daquele mês. |
| Custo Mensal | BRL | monetary, `total` | Valor cobrado pelo medidor naquele período. |
| Consumo Anual | m³ | water / gas, `total` | Volume acumulado desde a primeira leitura do ano. |

Todo sensor expõe `meter_code`, `year` e `month` como atributos, para que você
saiba a qual período de cobrança o estado se refere. O portal publica as
leituras uma vez por mês, então o intervalo padrão de consulta é de uma hora
(configurável nas opções da integração).

## Histórico e o painel de Energia

O estado de um sensor traz apenas a última leitura publicada, então o histórico
mês a mês que o portal guarda é importado para as estatísticas de longo prazo
do Home Assistant. Cada medidor recebe duas estatísticas externas:

| Id da estatística | Unidade | O que guarda |
|---|---|---|
| `metragen:<code>_<kind>` | m³ | Volume de cada mês, com a leitura do medidor como estado |
| `metragen:<code>_<kind>_cost` | BRL | Valor cobrado em cada mês |

`<code>` é o código do medidor exibido no portal e `<kind>` é `water` ou `gas`,
por exemplo `metragen:af1234_water` ou `metragen:aq1234_gas`. As séries têm o
mesmo nome dos dispositivos dos medidores ("AF1234 Água Fria", "AQ1234 Gás"),
então o seletor do painel de energia lê igual à lista de dispositivos. O valor
de cada mês cai no primeiro dia daquele mês.

A primeira atualização volta um ano de cada vez até o portal não informar
nenhum medidor (no máximo 10 anos); as seguintes só acrescentam meses mais
novos que o último armazenado. Escolha a estatística de consumo como fonte de
água ou gás em *Configurações → Painéis → Energia*, ou plote qualquer uma das
séries com um card de gráfico de estatísticas. Remover a integração mantém as
estatísticas; exclua-as em *Ferramentas de desenvolvedor → Estatísticas* se não
as quiser mais.

## Instalação

### HACS

1. Adicione `https://github.com/roquerodrigo/ha-metragen` como repositório
   personalizado do tipo *Integração*, ou clique no badge acima.
2. Instale **Metragen** e reinicie o Home Assistant.
3. Vá em *Configurações → Dispositivos e serviços → Adicionar integração*,
   escolha **Metragen** e informe o código ou e-mail e a senha que você
   cadastrou no portal do morador (o formulário *Registre-se*).

### Manual

Copie `custom_components/metragen/` para o diretório `custom_components/` da
sua configuração do Home Assistant e reinicie.

## Como funciona

O portal não tem API pública; a integração usa os mesmos endpoints que a área
do morador do site usa:

1. `POST /Portal/AcessoAoPortal` com o código ou e-mail e a senha que o morador
   cadastrou no portal. Um login rejeitado redireciona de volta à página de
   login em vez de falhar a requisição.
2. `POST /Portal/AreaMorador` e `POST /Portal/FiltroAno` selecionam a área do
   morador e o ano na sessão mantida no servidor.
3. `POST /Portal/LeiturasMorador_Read` e `POST /Portal/LeiturasMoradorGas_Read`
   retornam os grids de água e de gás em JSON. Um corpo vazio significa que a
   sessão expirou, então o cliente entra de novo e tenta mais uma vez.

As leituras são publicadas mensalmente, então no começo do ano o ano corrente
pode ainda não ter linhas; cada tipo sem linhas recai no ano anterior, para que
a última leitura continue sendo informada na virada do ano. Quedas curtas do
portal são absorvidas por 24 horas antes de as entidades ficarem indisponíveis,
e credenciais rejeitadas iniciam o fluxo de reautenticação.

## Desenvolvimento

```bash
scripts/setup                              # cria o .venv e instala as dependências (uv sync)
scripts/develop                            # inicia o Home Assistant em modo debug com a integração carregada
scripts/lint                               # ruff format --check, ruff check, mypy e pytest
uv run ruff format --check .               # confere a formatação
uv run ruff check .                        # lint
uv run mypy custom_components/metragen     # checagem de tipos
uv run pytest                              # roda os testes com o gate de 90 % de cobertura
```

Os dois scripts rodam pelo `uv`, que gerencia o `./.venv` automaticamente. O HA
roda com a configuração em `config/` e o `PYTHONPATH` apontando para
`custom_components/` — sem symlinks. Para recriar os ids de entidades e
dispositivos durante o desenvolvimento:

```bash
rm config/.storage/core.entity_registry config/.storage/core.device_registry
```

### Testando no Docker

O `compose.yaml` roda a versão do Home Assistant em que os testes estão
fixados, com `config/` como diretório de configuração e
`custom_components/metragen/` montado como somente leitura dentro dele, de modo
que o container sempre roda a árvore de trabalho:

```bash
docker compose up -d          # inicia o Home Assistant em http://localhost:8123
docker compose logs -f        # acompanha o log (a integração loga em nível debug)
docker compose restart        # recarrega a integração após uma mudança no código
docker compose down           # para; config/ mantém o onboarding, os usuários e as entries
```

Na primeira inicialização, conclua o onboarding e depois adicione **Metragen**
em *Configurações → Dispositivos e serviços*. O `config/` é compartilhado com o
`scripts/develop`, então não rode os dois ao mesmo tempo.

As convenções para quem contribui ficam em [`CODE_STYLE.md`](./CODE_STYLE.md);
as notas de arquitetura para agentes de IA, em [`CLAUDE.md`](./CLAUDE.md).
Instale os hooks de pre-commit uma vez por clone com `pre-commit install`.

## Estrutura

```
custom_components/metragen/
├── __init__.py        # async_setup_entry / unload / reload / remoção de dispositivo
├── api.py             # cliente do portal: login, seleção de ano, leitura dos grids
├── brand/             # assets da marca
├── config_flow.py     # passos user / reauth / reconfigure
├── const.py           # DOMAIN, LOGGER, URL do portal, ATTRIBUTION, padrões de scan interval
├── coordinator.py     # DataUpdateCoordinator com fallback de ano e carência para quedas
├── data/              # um TypedDict/dataclass por arquivo; aliases de tipo no __init__.py
│   ├── meter.py       # MetragenMeter: código, tipo, leituras, valores derivados
│   ├── meter_kind.py  # water / gas
│   ├── meter_reading.py
│   ├── readings.py    # medidores de um ano, por tipo
│   ├── reading_row.py # formato bruto da linha do grid
│   ├── read_response.py
│   └── …              # formatos de config, opções, diagnóstico e runtime
├── diagnostics.py     # diagnóstico para download, com as credenciais ocultadas
├── entity.py          # CoordinatorEntity base vinculada a um medidor
├── exceptions/        # um arquivo por classe de exceção
├── icons.json         # ícones das entidades indexados por translation_key
├── manifest.json
├── options_flow.py    # OptionsFlow com scan_interval
├── repairs.py         # plataforma de reparos
├── sensor/            # um arquivo por classe de sensor
└── translations/
    ├── en.json
    └── pt-BR.json
```

## CI

Todos os workflows chamam os workflows reutilizáveis de [`roquerodrigo/workflows`](https://github.com/roquerodrigo/workflows):

- **`ci.yml`** — ruff (check + format) + mypy, pytest com o gate de cobertura e validação `hassfest` (o validador do HACS fica desligado enquanto o repositório for privado); push/PR para a `main`
- **`release.yml`** — release-please, condicionado a um CI verde na `main`
- **`auto-assign.yml`** — atribui novas issues/PRs ao code owner

## Licença

[MIT](LICENSE)
