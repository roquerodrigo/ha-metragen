# Assets da marca

O Home Assistant 2026.3 e posteriores servem as imagens deste diretório
diretamente (`/api/brands/integration/metragen/<image>`), com prioridade sobre
o CDN do [home-assistant/brands](https://github.com/home-assistant/brands),
então a integração mostra o próprio ícone sem precisar de uma submissão ao
brands. A versão mínima do Home Assistant no `hacs.json` está acima disso,
então toda instalação suportada conta com esse comportamento.

| Arquivo       | Conteúdo                                       | Tamanho  |
| ------------- | ---------------------------------------------- | -------- |
| `icon.png`    | Símbolo da Metragen                            | 256×256  |
| `icon@2x.png` | Símbolo da Metragen                            | 512×512  |
| `icon.svg`    | o PNG 800×800 do símbolo em um contêiner SVG   | quadrado |

A origem é o símbolo que a Metragen publica em
`https://metragen.com.br/wp-content/uploads/2022/08/metragen-favicon.png`
(PNG 800×800 com transparência), redimensionado com filtro Lanczos.

Nenhum `logo.png` é distribuído, de propósito: o Home Assistant recai no
`icon.png` sempre que um logo é pedido (o mesmo vale para as variantes `@2x` e
`dark_`), e a única arte horizontal que a Metragen publica tem 258×51 pixels,
pequena demais para ampliar sem borrar. Adicione `logo.png` (menor lado entre
128 e 256 px) e `logo@2x.png` (256 a 512 px) se um logotipo em alta resolução
ou vetorial ficar disponível.
