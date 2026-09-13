# Brand assets

Home Assistant 2026.3 and later serve the images in this directory directly
(`/api/brands/integration/metragen/<image>`), taking priority over the
[home-assistant/brands](https://github.com/home-assistant/brands) CDN, so the
integration shows its own icon without a brands submission. The minimum Home
Assistant version in `hacs.json` is above that, so every supported install
gets it.

| File          | Content                                    | Size    |
| ------------- | ------------------------------------------ | ------- |
| `icon.png`    | Metragen symbol                            | 256×256 |
| `icon@2x.png` | Metragen symbol                            | 512×512 |
| `icon.svg`    | the 800×800 symbol PNG in an SVG container | square  |

The source is the symbol Metragen publishes at
`https://metragen.com.br/wp-content/uploads/2022/08/metragen-favicon.png`
(800×800 PNG with transparency), scaled with Lanczos filtering.

No `logo.png` is shipped on purpose: Home Assistant falls back to `icon.png`
wherever a logo is requested (same for the `@2x` and `dark_` variants), and
the only horizontal artwork Metragen publishes is 258×51 pixels, too small to
enlarge without blurring. Add `logo.png` (shortest side 128–256 px) and
`logo@2x.png` (256–512 px) if a high-resolution or vector wordmark becomes
available.
