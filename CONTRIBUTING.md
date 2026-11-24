# Contribuindo

Relatos de bug, ideias e pull requests são bem-vindos. Issues, commits e pull
requests são escritos em português do Brasil. O código continua em inglês
(veja a seção "Idioma" do [CODE_STYLE.md](CODE_STYLE.md)).

## Relatando um bug

Abra uma [issue](https://github.com/roquerodrigo/ha-metragen/issues/new/choose)
com:

- a versão do Home Assistant e a da integração;
- o que você fez, o que esperava e o que aconteceu;
- os diagnósticos baixados no menu da integração (o login, a senha e os
  códigos dos medidores são removidos) e as linhas relevantes do log de
  depuração.

## Ambiente de desenvolvimento

O projeto usa o [uv](https://docs.astral.sh/uv/), que cria e gerencia o
`.venv/` sozinho.

```bash
scripts/setup      # instala as dependências no .venv
scripts/develop    # roda o Home Assistant em http://localhost:8123 com a integração carregada
```

O `scripts/develop` usa a configuração em [`config/`](config/) e coloca
`custom_components/` no `PYTHONPATH`, sem symlink. Para recriar os ids de
entidades e dispositivos, apague `config/.storage/core.entity_registry` e
`config/.storage/core.device_registry` com o Home Assistant parado.

### Docker

O [`compose.yaml`](compose.yaml) roda a mesma versão do Home Assistant usada
nos testes, com `config/` como configuração e `custom_components/metragen/`
montado somente leitura, de modo que o container sempre roda a árvore de
trabalho.

```bash
docker compose up -d          # inicia o Home Assistant em http://localhost:8123
docker compose logs -f        # acompanha o log
docker compose restart        # recarrega a integração depois de mudar o código
docker compose down           # para o container, config/ mantém os dados
```

O `config/` é compartilhado com o `scripts/develop`, então não rode os dois ao
mesmo tempo.

## Checagens

Rode antes de abrir um pull request. O CI roda as mesmas, e o
`pre-commit install` faz as três primeiras rodarem a cada commit.

```bash
uv run ruff format --check .              # formatação
uv run ruff check .                       # lint
uv run mypy custom_components/metragen    # tipos
uv run pytest                             # testes, a cobertura precisa ficar em 90 % ou mais
```

O `scripts/lint` roda os quatro comandos em sequência.

Leia o [CODE_STYLE.md](CODE_STYLE.md) antes de criar ou reorganizar código.

## Estrutura

```
custom_components/metragen/
├── __init__.py        # setup, unload, reload e exclusão de dispositivos
├── api.py             # cliente do Portal do Morador: login, seleção de ano, leitura dos grids
├── brand/             # ícones da integração
├── config_flow.py     # passos user, reauth e reconfigure
├── const.py           # domínio, URL do portal e intervalo de consulta padrão
├── coordinator.py     # atualização com fallback de ano e carência de 24 horas para quedas
├── data/              # um TypedDict ou dataclass por arquivo, aliases de tipo no __init__.py
├── diagnostics.py     # diagnóstico com login, senha e códigos de medidor ocultados
├── entity.py          # entidade base vinculada a um medidor
├── exceptions/        # um arquivo por exceção
├── icons.json         # ícones das entidades
├── manifest.json
├── options_flow.py    # intervalo de consulta
├── repairs.py         # plataforma de reparos
├── sensor/            # um arquivo por sensor
├── statistics.py      # importação do histórico mensal para as estatísticas de longo prazo
└── translations/      # en.json e pt-BR.json
```

## CI

- `ci.yml`: ruff e mypy, pytest com o gate de cobertura, a validação do
  Home Assistant Marketplace, o hassfest e o HACS action, em todo pull request
  e push na `main`.
- `codeql.yml`: análise de segurança do código.
- `release.yml`: depois de um CI verde na `main`, o
  [Release Autopilot](https://github.com/marketplace/actions/release-autopilot)
  mantém o pull request de release e, quando uma versão sai, anexa a ela o
  `metragen.zip`.
- `auto-assign.yml`: atribui issues e pull requests novos ao mantenedor.

## Pull requests

1. Faça um fork do repositório e crie a sua branch a partir da `main`.
2. Escreva as mensagens de commit no
   [Conventional Commits](https://www.conventionalcommits.org/), com o tipo e o
   escopo em inglês e o assunto em português
   (`fix(sensor): corrige o consumo anual na virada do ano`). As versões e as
   notas de release são geradas a partir delas. Marque mudanças que quebram a
   compatibilidade com `!` ou com o rodapé `BREAKING CHANGE:`.
3. Atualize `translations/en.json` e `translations/pt-BR.json` juntos quando
   mudar textos exibidos ao usuário. O `tests/test_translations.py` falha se
   as chaves divergirem.
4. Atualize o README quando o comportamento, a configuração ou as entidades
   mudarem.
5. Preencha o template do pull request.

## Licença

As contribuições são publicadas sob a [licença MIT](LICENSE) do projeto.
