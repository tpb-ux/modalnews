# Auditoria técnica: Modal News (12/10/2026)

Metodologia: rebuild local (`build.py`, 1.512 HTML), varredura com BeautifulSoup de todas as páginas, validação dos sitemaps, checagens com curl no site em produção, Lighthouse mobile (7 URLs), histórico do GitHub Actions (`gh run list`) e leitura do código. Todos os números abaixo foram medidos; nada foi estimado.

## Notas
| Área | Nota |
|---|---|
| 1. SEO técnico | 80 |
| 2. Desempenho | 98 |
| 3. Acessibilidade (automatizada) | 95 |
| 4. Automação/robustez | 60 |
| 5. Segurança | 85 |
| 6. Conteúdo/legal | 65 |
| 7. GEO/IA | 72 |
| 8. Replicabilidade | 45 |
| **Geral (média ponderada)** | **73** |

**Veredito de produção: CONDICIONAL.** A base técnica está boa: velocidade, canonicals, sitemaps e schema estão em ordem. Antes de considerar o portal pronto, falta corrigir os links quebrados, confirmar que o cron roda de fato e publicar contato e termos.
**Veredito de replicação: NÃO, ainda não.** Hoje a estrutura serve de referência, mas não é um template: a lógica de logística está fixa no código.

## O que está bom (medido)
- 1.512 HTML: 38 redirects (stubs com noindex e canonical), 97 noindex, **1.377 indexáveis**. Os sitemaps têm exatamente essas 1.377 URLs: nenhuma inexistente, nenhuma noindex e nenhum redirect neles.
- Zero canonical divergente, zero título duplicado, zero descrição duplicada. Todas as páginas têm `lang`. Nenhuma página indexável ficou órfã.
- JSON-LD sem nenhum erro de parse. Tipos presentes: NewsMediaOrganization/WebSite (1.474), BreadcrumbList (1.413), FAQPage (1.387), Dataset (1.163), DefinedTerm, Airport, NewsArticle etc.
- Imagens: 3.136 `<img>`, todas com `alt`, `width` e `height`, o que evita CLS. São 240 arquivos em static/img, todos WebP, com média de 50,8 KB.
- Lighthouse mobile ao vivo deu 100/100/100/100 (Desempenho, Acessibilidade, Boas práticas, SEO) em todas as 7 URLs: `/`, `/glossario/danfe/`, `/diesel/sao-paulo-sp/`, `/rotas/belo-horizonte-mg-x-itaguai-rj/`, `/logistica/campinas-sp/`, `/transporte/`, `/aeroportos/sbgr/`. LCP ficou entre 0,8 e 1,1 s, CLS 0 e TBT ≤ 30 ms. Peso: 505 KiB na home, 499 KiB nas editorias e 12 a 33 KiB nas pSEO.
- HTTPS ativo (https_enforced=true). `www` e `tpb-ux.github.io/modalnews/` respondem 301 para o domínio. 404 real em URL inexistente. Sem barra final, 301 para a versão com barra.
- Cada matéria tem crédito da fonte, crédito da imagem, link "Leia na íntegra" e aviso de direitos. As matérias agregadas estão em `noindex,follow` por design (68 noindex; 7 indexáveis são os resumos semanais).
- Nenhum segredo no repositório (grep por key/token/secret/ghp_). A chave do IndexNow é pública por natureza.

## Achados priorizados

### CRÍTICO
1. **Cron nunca rodou.** As últimas 28 execuções foram todas por `push` ou `workflow_dispatch`, sem nenhuma por `schedule`. As 29 matérias em `content/` são todas de 2026-10-09, e `max_idade_dias: 3` faz com que nada mais antigo entre. Se o agendamento não disparar, a home congela. *Correção:* acompanhar as próximas janelas (:17 a cada 3 h). Se continuar sem disparar, fazer um commit no workflow para reativar o schedule, já que o repo foi criado hoje e o GitHub às vezes atrasa ou ignora o cron. Vale também um alerta, por exemplo uma issue automática, quando a matéria mais recente tiver mais de 24 h.
2. **313 links internos quebrados, para 16 destinos (404 em produção).** Exemplos: `/rodovias/br-40/` (59 links; o certo seria br-040, ou a página não existe), `/rodovias/br-50/` (50), `/pedagios/ecovias-minas-gois/` (50; o acento sumiu do slug), `/pedagios/motiva-paran/` (27), `/pedagios/epr-via-mineira/` (21), `/rodovias/br-60/`, `/pedagios/concer/`, `/pedagios/elovias/`, `/pedagios/rota-verde-gois/`, `/rodovias/151/`. A origem são as páginas `/rotas/*` (paginas8.py:26 linka rodovias e concessões sem checar se a página existe) e o slugify aplicado a nomes com acento ou mal codificados. Confirmado ao vivo: `https://modalnews.com.br/rodovias/br-40/` retorna 404. *Correção:* gerar os links somente quando o destino existe (como já é feito na linha 29) e normalizar o número da BR com zero-padding e acentos via `unicodedata`. Depois, incluir uma checagem de links no build que falhe o CI.

### ALTO
3. **Regra de ≥5 FAQs não cumprida em 865 das 1.377 indexáveis.** Distribuição: diesel 420, rotas 238, aeroportos 44, portos 29, pedágios 20, estados 19, rodovias 17, glossário 16, comparativos 13, frete-mínimo 12, tipos-de-carga 8, resumo-semanal 8, utilidades 3, home 1, veículos 1. Diesel e rotas têm 4 perguntas no FAQPage; aeroportos têm 3. *Correção:* adicionar 1 a 2 perguntas, alimentadas por dados, em cada template.
4. **Conteúdo quase duplicado nas pSEO.** Medido por Jaccard de trigramas, com números normalizados, numa amostra de 12 páginas por família: aeroportos média 0,68; rotas 0,66 (máx 0,84); logística/cidade 0,60 (máx 0,86); diesel 0,59 (máx 0,79); pedágios 0,47. O glossário ficou em 0,12, que é saudável. Há risco de "scaled content" e de as páginas caírem em "rastreada, não indexada". *Correção:* incluir blocos condicionais por dado (ranking no estado, variação semanal, hubs próprios, comparação com vizinhas) e aplicar noindex abaixo de um limiar de dados únicos. Acompanhar a cobertura no Search Console nas primeiras semanas.
5. **Falta contato e termos.** `empresa.email` e `redes` estão vazios, e não existem `/contato/` nem `/termos/`. A privacidade cita a LGPD 1 vez, mas sem canal do encarregado ou e-mail. Isso pesa em E-E-A-T e em Google News, e o direito do titular exige um canal. *Correção:* preencher o e-mail e criar as páginas de termos e contato, com DPO/canal LGPD.
6. **Direito de imagem.** As fotos das fontes são republicadas em 1200px (por exemplo `imagem_origem` de frotacia.com.br), com crédito mas sem licença. Foi escolha do usuário, e o risco jurídico e de DMCA continua. *Correção mínima:* publicar uma política de remoção rápida (takedown) com contato, ou usar apenas a miniatura de 480px.

### MÉDIO
7. **Falha recente no workflow (07:02).** O job indexnow terminou com `fatal: pathspec 'data/indexnow_hashes.json' did not match`. A execução seguinte passou. Além disso, o job indexnow refaz o build e faz push separadamente do job build, o que abre risco de corrida (push rejeitado) quando há coleta. *Correção:* gerar os hashes no job build e usar `git pull --rebase` antes do push.
8. **Falhas mascaradas.** Todos os coletores rodam com `|| echo ...`, então o workflow nunca falha. Quando a coleta de 03:54 registrou o erro "Portal NTC&Logística: sem itens", apenas `data/saude_coleta.json` guardou o registro. *Correção:* gerar um alerta quando houver feed com erro por mais de N execuções seguidas ou zero matérias novas em 24 h.
9. **7 páginas sem `<h1>`**, incluindo a home (`/`) e as editorias (`/mercado/`, `/armazenagem/`, `/transporte/`...). *Correção:* um h1 por página (pode ser visualmente discreto).
10. **30 Article (veículos e tipos de carga) sem `image`** no schema, por exemplo `/veiculos/cegonha/`, o que tira a elegibilidade a rich results. *Correção:* usar a imagem padrão da editoria.
11. **llms.txt desatualizado.** São 1.466 bytes que citam glossário, diesel e calculadoras, mas não mencionam cidades (391), rotas (237), aeroportos (43), pedágios (30) e expediente. *Correção:* gerar a partir das famílias de páginas e incluir `llms-full.txt` com dados citáveis (tabelas de diesel e distâncias).
12. **63 indexáveis com menos de 300 palavras**: estados 15, pedágios 14, glossário 10, diesel por UF pequena 4, além de `/veiculos/` (123) e `/rodovias/` (191). *Correção:* enriquecer ou aplicar noindex.

### BAIXO
13. 17 títulos com mais de 65 caracteres (por exemplo `/diesel/livramento-de-nossa-senhora-ba/`). 7 descrições fora da faixa de 50 a 165 caracteres (as editorias).
14. GitHub Pages não permite HSTS/CSP/X-Frame próprios (o servidor manda só `cache-control: max-age=600`). Aceitável. Se precisar, Cloudflare na frente. HTTP:80 não pôde ser testado deste ambiente (timeout); conferir no navegador.
15. Dependências sem versão fixada (`requirements.txt` sem pins) e actions referenciadas por tag, não por SHA. Permissão `contents: write` ampla. *Correção:* fixar as versões e ativar o Dependabot.
16. Crescimento do repo: 25,7 MB no GitHub (.git local com 32 MB). Imagens com média de 50,8 KB e cerca de 2 arquivos por matéria, o que dá algo como 100 KB por matéria. No limite de 20 matérias por execução e 8 execuções por dia, o pior caso é cerca de 16 MB/dia. *Correção:* rotação (apagar imagens de matérias com mais de 90 dias, que são noindex) ou guardar as imagens fora do git. O limite do Pages é 1 GB por site, com recomendação de repo abaixo de 1 GB. Cache OSRM: 4,2 MB versionado, aceitável.
17. Build rápido: 4,0 s localmente. Execuções no Actions levaram cerca de 1 a 2 min (por exemplo 07:03:34→07:05:22).

## Replicabilidade (por que 45)
- `config.yaml` cobre: nome, tagline, base_url, cname, editorias, fonte prioritária, empresa, verificações e IndexNow. `feeds.yaml` cobre as fontes. Essas partes estão boas.
- Fixo no código: 8 módulos `paginas*.py`, mais `glossario.py`, `relacionados.py`, `tarifas.py` e `tools/*`, todos específicos de logística (ANP, ANTT, OSRM, portos, aeroportos, pedágios). Há 41 menções literais a "Modal News"/modalnews nos .py, incluindo o User-Agent do fetch e textos de FAQ. Menu e rodapé estão fixos em `build.py` (linhas 49, 79 e 158, com links de diesel, frete e portos). As palavras de relevância e o bloqueio de temas estão no código ou nos feeds, não num arquivo de nicho.
- O robots, o noindex dos stubs, os sitemaps e o IndexNow já são genéricos.

### Plano para virar template
1. Separar o **core** (build, layout, SEO, schema, sitemaps, IndexNow, busca, fetch RSS, páginas institucionais) dos **módulos de nicho** (`nichos/logistica/*.py`). O core carrega os módulos listados em `config.yaml: modulos: [glossario, diesel, rotas...]`.
2. Levar para o config: menu, rodapé, chips da home, brand e UA, palavras de relevância e bloqueio, FAQs institucionais e textos de "sobre", "metodologia" e "política editorial" (via YAML ou Markdown).
3. Exigir na interface de módulo: `paginas() -> [Pagina(url, title, desc, body, schema, faqs>=5, indexavel)]`. O core valida FAQs, tamanho, links e duplicidade e só então escreve.
4. Colocar o **CI de qualidade** no workflow: link-checker interno, ≥5 FAQs, título e descrição únicos, sitemap só com 200, Lighthouse CI numa amostra. O build falha se algum desses quebrar.
5. Ter um repo "template" no GitHub (Use this template) mais um script `novo_portal.py` (nome, domínio, editorias, feeds) e um checklist de lançamento (DNS, Search Console, Bing, e-mail, termos).
6. Gerar o llms.txt automaticamente e incluir o alerta de cron e feeds parados no core.

## Ordem sugerida de correção
1) Links quebrados com link-check no CI. 2) Confirmar o cron e criar o alerta de matéria parada. 3) Contato, termos e canal LGPD. 4) FAQs ≥5 em diesel, rotas, aeroportos e portos. 5) Diferenciação ou noindex das pSEO quase duplicadas. 6) h1, image no Article e llms.txt. 7) Refatorar em core + nicho e transformar em template.

---
## Correções aplicadas (12/10/2026)
| Métrica | Antes | Depois |
|---|---|---|
| Links internos quebrados | 313 (16 destinos) | 0 (build falha se houver) |
| Indexáveis com <5 FAQs | 865 | 0 |
| Páginas sem h1 | 7 | 0 |
| Article sem image | 30 | 0 |
| Títulos >65 / descrições fora de 50–165 | 17 / 7 | 0 / 0 |
| Indexáveis (sitemap) | 1.377 | 1.375 (+/contato/ e /termos/; 4 pSEO <300 palavras em noindex) |
| Jaccard médio (máx), mesma amostra | diesel 0,59 (0,79) · rotas 0,66 (0,84) · cidades 0,60 (0,86) · aeroportos 0,68 (0,72) | diesel 0,50 (0,77) · rotas 0,58 (0,80) · cidades 0,59 (0,72) · aeroportos 0,61 (0,70) |

- Workflow: coletores com `continue-on-error` + passo "Alertas" que abre/atualiza/fecha a issue "Alerta automático: coleta do Modal News" (matéria >24 h, feed com erro, passo falho); IndexNow usa a lista do build (artifact) e mescla hashes sobre o main atual; coleta commita com `[skip ci]` e rebase/retry.
- Pendências: cron agendado ainda sem execução registrada (workflow reativado); feed da NTC devolve vazio a partir dos runners do GitHub (funciona fora deles); e-mail de contato e encarregado LGPD a preencher em `config.yaml`.
