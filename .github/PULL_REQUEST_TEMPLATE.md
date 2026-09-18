## Resumo

<!-- 1 a 3 itens descrevendo o que mudou e por quê. -->

## Tipo de mudança

- [ ] Correção de bug
- [ ] Nova funcionalidade
- [ ] Refatoração / limpeza
- [ ] Documentação
- [ ] Ferramental / CI

## Plano de teste

- [ ] `uv run ruff format --check .`, `uv run ruff check .` e `uv run mypy custom_components/metragen` passam
- [ ] `pytest` passa com o gate de 90 % de cobertura
- [ ] Todos os locales de tradução atualizados (se strings voltadas ao usuário mudaram)

## Checklist

- [ ] O código está em inglês; docstrings, comentários, commits e este PR estão em pt-BR
- [ ] Termos nativos do domínio não foram traduzidos
- [ ] Uma classe de nível superior por arquivo
- [ ] CLAUDE.md / README atualizados se a arquitetura ou o fluxo de trabalho mudou
- [ ] Versão do `manifest.json` atualizada, se for uma release
