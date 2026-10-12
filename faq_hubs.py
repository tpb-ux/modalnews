"""FAQs das páginas de índice/hub (home, editorias e listas), derivadas dos dados do próprio site.
Registra em B.HUB_FAQ; build.page() injeta o bloco e o FAQPage quando a página não tem FAQ próprio."""
import json, yaml, datetime as dt
from paginas import brl, dbr, UFN

def build(B, posts):
    R = B.ROOT; H = B.HUB_FAQ; site = B.CFG["site_name"]
    rd = lambda f: json.loads((R / "data" / f).read_text(encoding="utf-8"))
    ry = lambda f: yaml.safe_load((R / "data" / f).read_text(encoding="utf-8"))
    db = rd("diesel.json"); cur = db["semanas"][max(db["semanas"])]; per = f"{dbr(cur['ini'])} a {dbr(cur['fim'])}"; br10 = cur["brasil"]["BR"]["s10"]["media"]
    rot = rd("rotas.json")["rotas"]; rod = rd("rodovias.json")["rodovias"]; feeds = ry("../feeds.yaml") if False else yaml.safe_load((R / "feeds.yaml").read_text(encoding="utf-8"))
    nf = len(feeds["feeds"]); fontes = ", ".join(f["nome"] for f in feeds["feeds"][:6])
    V = ry("veiculos.yaml"); T = ry("tipos_carga.yaml"); C = ry("comparativos.yaml"); G = ry("guias.yaml"); G = G.get("guias", G) if isinstance(G, dict) else G
    fm = rd("frete_minimo.json")["ato"]
    npr = sum(len(r["pracas"]) for r in rod.values())
    H["/"] = [
        (f"O que é o {site}?", f"Um portal de notícias e dados de logística, transporte, supply chain e comércio exterior, com curadoria automática de {nf} fontes do setor e páginas de referência baseadas em dados oficiais."),
        ("Qual o preço médio do diesel no Brasil nesta semana?", f"Na semana de {per}, o diesel S10 custou em média {brl(br10)} por litro, segundo o levantamento da ANP. Veja por estado e cidade na página de diesel."),
        ("De onde vêm as notícias?", f"De feeds RSS públicos de portais especializados, como {fontes}. Cada notícia traz resumo curto, crédito e link para o original."),
        ("Com que frequência o site é atualizado?", "As notícias são coletadas a cada 30 minutos; diesel, tarifas de pedágio e frete mínimo são atualizados quando ANP e ANTT publicam novos dados."),
        ("Que ferramentas gratuitas o portal oferece?", f"Glossário de logística, calculadoras de cubagem, custo de diesel e frete mínimo ANTT, além de {len(rot)} rotas entre cidades e portos com distância, pedágios e piso de frete."),
    ]
    agora = dt.datetime.now(dt.timezone.utc)
    for s, nome in B.EDS.items():
        ps = [p for p in posts if p["editoria"] == s]; src = sorted({p.get("fonte", "") for p in ps if p.get("fonte")})
        ult = ps[0] if ps else None
        H[f"/{s}/"] = [
            (f"Quais as últimas notícias de {nome.lower()}?", (f"A mais recente é \"{ult['titulo']}\" ({ult.get('fonte', '')}, {ult['data']:%d/%m/%Y}). " if ult else "") + f"A editoria reúne {len(ps)} notícia(s) no momento, sempre com link para a fonte."),
            (f"Quais fontes aparecem em {nome}?", (", ".join(src) + "." if src else "Portais especializados do setor listados na política editorial.") + " A lista completa de fontes está no repositório do site."),
            ("As notícias são reescritas pelo portal?", "Não. Publicamos o título original, um resumo curto do feed e o link \"Leia na íntegra\" para a fonte."),
            ("Como as notícias são classificadas nesta editoria?", "Pela editoria definida para a fonte ou, quando a fonte é geral, por palavras-chave do título e do resumo; itens fora do tema são filtrados."),
            ("Com que frequência a editoria é atualizada?", "A coleta roda a cada 30 minutos; a página é regenerada a cada coleta."),
        ]
    H["/veiculos/"] = [("Quantos tipos de veículo de carga o guia cobre?", f"{len(V)} configurações: " + ", ".join(v["curto"] for v in V) + "."),
        ("Qual veículo de carga tem mais eixos no guia?", (lambda m: f"{m['curto']}, com {m['eixos']} eixos.")(max(V, key=lambda v: v.get("eixos", 0)))),
        ("De onde vêm os limites de peso por eixo?", "Da Resolução CONTRAN 882/2021, que fixa os limites por eixo e por conjunto e o peso bruto total combinado."),
        ("Como o número de eixos afeta o frete mínimo?", f"Na tabela da ANTT ({fm['nome']}), cada número de eixos tem coeficientes próprios de deslocamento (por km) e de carga e descarga."),
        ("Qual veículo é usado em entregas urbanas?", "O VUC (Veículo Urbano de Carga), de menor porte, aceito em zonas de restrição de muitos municípios, que definem as regras locais.")]
    H["/tipos-de-carga/"] = [("Quantos tipos de carga a tabela da ANTT considera?", f"A Tabela A do frete mínimo tem {len(rd('frete_minimo.json')['tabelas']['A']['cargas'])} tipos de carga; o guia explica {len(T)} deles."),
        ("Por que o tipo de carga muda o frete mínimo?", "Porque cada tipo exige implemento e operação diferentes, e a ANTT fixa coeficientes próprios para cada um."),
        ("O que é carga perigosa?", "Produto classificado como perigoso pela regulamentação da ANTT, que exige motorista com curso MOPP, rótulos de risco e documentação específica."),
        ("Qual a diferença entre granel e carga geral?", "Granel é transportado sem embalagem, direto no implemento (sólido ou líquido); carga geral é embalada ou unitizada, em caixas, paletes ou volumes."),
        ("Onde calcular o frete por tipo de carga?", "Na calculadora de frete mínimo, que usa os coeficientes oficiais da ANTT para cada tipo de carga e número de eixos.")]
    H["/comparativos/"] = [("Quantos comparativos há no portal?", f"{len(C)}: " + ", ".join(f"{c['na']} × {c['nb']}" for c in C) + ".")] + [(f"Qual a diferença entre {c['na']} e {c['nb']}?", c["intro"]) for c in C[:4]]
    H["/guias/"] = [("Quais guias práticos estão disponíveis?", ", ".join(g["titulo"] for g in G) + ".")] + [(f"O que o guia \"{g['titulo']}\" explica?", g.get("descricao", g["titulo"])) for g in G[:4]]
    if len(H["/guias/"]) < 5: H["/guias/"].append(("Os guias citam fontes oficiais?", "Sim. Cada guia lista as normas e páginas oficiais usadas, como Receita Federal, Sefaz e ANTT."))
    rk = sorted(rod.items(), key=lambda x: -len(x[1]["pracas"]))
    H["/rodovias/"] = [("Quantas rodovias federais concedidas o portal acompanha?", f"{len(rod)} rodovias com {npr} praças de pedágio ativas no cadastro da ANTT."),
        ("Qual rodovia federal tem mais praças de pedágio?", f"A {rk[0][0]}, com {len(rk[0][1]['pracas'])} praças, seguida pela {rk[1][0]} ({len(rk[1][1]['pracas'])})."),
        ("De onde vêm os dados de tráfego?", "Do volume de tráfego por praça de pedágio publicado pela ANTT em dados abertos, separado em veículos comerciais, de passeio e motos."),
        ("Rodovias estaduais estão incluídas?", "Não. Só trechos federais concedidos e regulados pela ANTT; rodovias estaduais têm agências e tarifas próprias."),
        ("Onde ver as tarifas por concessionária?", "Na página de pedágios, com tarifas por praça para automóvel e caminhões de 2, 5 e 6 eixos.")]
    H["/pedagios/"] = [("Como se calcula o pedágio de caminhão?", "Nas rodovias federais, a tarifa de veículo comercial é a tarifa básica multiplicada pelo número de eixos."),
        ("Eixo suspenso paga pedágio?", "Pela Lei 13.103/2015, caminhões vazios não pagam pelos eixos suspensos nas rodovias federais concedidas."),
        ("Quem paga o pedágio no transporte de carga?", "O embarcador, por meio do Vale-Pedágio obrigatório (Lei 10.209/2001), separado do valor do frete."),
        ("Quantas praças de pedágio federais existem?", f"O cadastro da ANTT usado pelo portal tem {npr} praças ativas em {len(rod)} rodovias federais concedidas."),
        ("As tarifas estão atualizadas?", "Vêm das tabelas publicadas pela ANTT para cada concessão; a data de atualização aparece em cada página.")]
    lr = sorted(rot, key=lambda r: -r["km"])
    H["/rotas/"] = [("Quantas rotas de frete o portal calcula?", f"{len(rot)} rotas entre grandes cidades e delas até os principais portos."),
        ("Qual a rota mais longa da lista?", f"{lr[0]['a']['nome']} ({lr[0]['a']['uf']}) a {lr[0]['b'].get('porto_nome') or lr[0]['b']['nome']}, com cerca de {f"{round(lr[0]['km']):,}".replace(",", ".")} km por estrada."),
        ("Como a distância é calculada?", "Pelo roteador OSRM com dados do OpenStreetMap, entre os centros dos municípios."),
        ("Os pedágios estaduais estão incluídos?", "Não. Só praças federais (ANTT) a até 250 m do traçado calculado."),
        ("Como é calculado o frete mínimo de cada rota?", f"Distância × coeficiente de deslocamento + coeficiente de carga e descarga, pela {fm['nome']}.")]
    est = sorted([(u, d["s10"]["media"]) for u, d in cur["estados"].items() if d.get("s10")], key=lambda x: x[1])
    H["/estados/"] = [("O que tem em cada página de estado?", "Diesel por cidade (ANP), rodovias federais com pedágio (ANTT), portos, aeroportos de carga e notícias do estado."),
        ("Qual estado tem o diesel mais barato?", f"Na semana de {per}, {UFN[est[0][0]]}, com S10 a {brl(est[0][1])}/l em média (ANP)."),
        ("Qual estado tem o diesel mais caro?", f"Na mesma semana, {UFN[est[-1][0]]}, com S10 a {brl(est[-1][1])}/l (ANP)."),
        ("Por que alguns estados não aparecem como página indexada?", "Estados com poucos dados oficiais disponíveis ficam fora dos buscadores até terem informação suficiente."),
        ("Os dados são oficiais?", "Sim: ANP, ANTT, ANTAQ, ANAC e IBGE, com a fonte indicada em cada bloco.")]
    H["/logistica/"] = [("O que tem nas páginas de logística por cidade?", "Distâncias por estrada até polos e portos, pedágios federais próximos, aeroporto de carga mais próximo, diesel e dados do IBGE."),
        ("Quantas cidades têm diesel pesquisado nesta semana?", f"{len(cur['municipios'])} municípios na semana de {per}, segundo a ANP."),
        ("Como são escolhidos os polos regionais?", "Pela hierarquia urbana do IBGE (REGIC), que define as cidades de influência de cada região."),
        ("As distâncias são em linha reta?", "Não: são por estrada, calculadas pelo OSRM com dados do OpenStreetMap; a linha reta aparece como referência."),
        ("Por que minha cidade não aparece?", "Só geramos páginas para municípios com dados oficiais suficientes, como preço do diesel pesquisado pela ANP.")]
    H["/resumo-semanal/"] = [("O que é o resumo semanal?", "Um balanço automático da semana com diesel (ANP), frete mínimo e tráfego (ANTT) e notícias publicadas no portal."),
        ("Qual foi o diesel médio da última semana?", f"Na semana de {per}, o S10 custou {brl(br10)}/l em média no Brasil (ANP)."),
        ("Quando sai um novo resumo?", "Quando a ANP publica o levantamento semanal de preços, normalmente no fim de semana."),
        ("Os resumos antigos ficam disponíveis?", "Sim, cada semana tem sua página permanente, com navegação para a anterior e a seguinte."),
        ("Os números são estimativas?", "Não. São os valores publicados pelas fontes oficiais, com link para os arquivos.")]
    H["/siglas/"] = [("Para que serve a lista de siglas?", "Para consultar rapidamente o significado de siglas de logística, transporte e comércio exterior, com link para o verbete do glossário quando existe."),
        ("O que significa CT-e?", "Conhecimento de Transporte Eletrônico, o documento fiscal da prestação de serviço de transporte de cargas."),
        ("O que significa MDF-e?", "Manifesto Eletrônico de Documentos Fiscais, que vincula os documentos da carga transportada numa viagem."),
        ("O que significa RNTRC?", "Registro Nacional de Transportadores Rodoviários de Cargas, mantido pela ANTT e obrigatório para o transporte remunerado."),
        ("O que significa WMS?", "Warehouse Management System, o sistema de gestão de armazém.")]
    H["/links-uteis/"] = [("Que tipo de link está nesta página?", "Órgãos públicos, consultas oficiais e entidades do setor de logística e transporte."),
        ("Onde consultar o RNTRC de uma transportadora?", "No portal da ANTT, na consulta pública do RNTRC."),
        ("Onde ver os preços oficiais do diesel?", "No Levantamento de Preços de Combustíveis da ANP; o portal organiza esses dados por cidade."),
        ("Onde consultar normas de peso e dimensões?", "Nas resoluções do CONTRAN, como a 882/2021, publicadas pelo Ministério dos Transportes."),
        ("Os links são patrocinados?", "Não. A lista não tem links pagos.")]
    H["/utilidades/"] = [("O que há na seção de utilidades?", "Tabelas de referência (contêineres e Incoterms) e calculadoras de cubagem, custo de diesel e frete mínimo."),
        ("As calculadoras enviam meus dados?", "Não. Os cálculos rodam no navegador."),
        ("Qual a versão dos Incoterms usada?", "Incoterms 2020, da Câmara de Comércio Internacional, com 11 regras."),
        ("Quanto mede um contêiner de 20 pés?", "Pela ISO 668, 6,058 m × 2,438 m × 2,591 m de medidas externas no modelo padrão."),
        ("Como calcular a cubagem?", "Volume em m³ (comprimento × largura × altura) multiplicado pelo fator de cubagem do modal.")]
    emp = B.CFG.get("empresa") or {}
    H["/expediente/"] = [("Quem é responsável pelo portal?", f"{emp.get('razao_social', '')}, CNPJ {emp.get('cnpj', '')}."),
        ("Onde fica a empresa?", ", ".join(x for x in [(emp.get("endereco") or {}).get("logradouro", ""), (emp.get("endereco") or {}).get("cidade", "")] if x) + "."),
        ("Como entrar em contato?", "Pelos canais listados na página de contato."),
        ("Quem escreve as notícias?", "As notícias são resumos automáticos de feeds públicos, com link para a fonte; o conteúdo próprio é o glossário e as páginas de dados."),
        ("Como pedir correção ou remoção?", "Pela política de correções e pela política de remoção descrita nos termos de uso.")]
