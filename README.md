# ERB Watching (Registros de Antenas 5G)

Este projeto tem como objetivo automatizar o processamento de dados e a geração de um mapa interativo das Estações Rádio Base (ERBs) - Antenas 5G. O sistema lê informações a partir de uma base de dados em Excel, processa as fotografias das antenas e cria uma visualização web interativa no mapa.

## Tecnologias Utilizadas
- **Python 3**
- **Pandas**: Para processamento e estruturação de dados.
- **Folium**: Para a criação e renderização do mapa interativo.
- **Pillow (PIL)**: Para o redimensionamento e otimização em lote das fotografias das ERBs.
- **Tqdm**: Para exibir o progresso durante o processamento das fotos.

## Estrutura do Projeto
- `build_site.py`: Script principal que orquestra todo o pipeline de execução.
- `process_data.py`: Trata os dados do arquivo Excel e processa/redimensiona as fotos originais paralelamente.
- `generate_map.py`: Gera o mapa interativo (`index.html`) agrupando as ERBs graficamente por operadora.
- `erb_photos/`: Diretório de entrada onde as fotos originais devem ser adicionadas.
- `processed_photos/`: Diretório de saída onde as imagens já redimensionadas e otimizadas são salvas.
- `preprocessing-dataset.ipynb`: Notebook auxiliar usado no pré-processamento dos dados iniciais.
- `requirements.txt`: Arquivo com todas as dependências do projeto.
- `index.html`: Arquivo final gerado pelo script, contendo o site/mapa.

## Como Executar

### 1. Instalar as dependências
Certifique-se de ter o Python instalado ou utilize seu ambiente virtual e execute o comando abaixo para instalar as bibliotecas necessárias:
```bash
pip install -r requirements.txt
```

### 2. Preparar os arquivos
- Certifique-se de haver um arquivo Excel com os dados (ex: `ERBs_Mar26_goiania_preprocessed.xlsx`) na raiz do projeto.
- Coloque as fotografias originais (referenciadas nos dados do Excel) dentro da pasta `erb_photos/`.

### 3. Construir o Mapa
Para rodar todo o fluxo de ponta a ponta (verificação, otimização das fotos e renderização do mapa), basta chamar o script principal:
```bash
python build_site.py
```

Se as imagens já estiverem processadas e você quiser apenas gerar um novo mapa (poupando tempo), use a flag `--skip-photos`:
```bash
python build_site.py --skip-photos
```

Ao final no processo, o arquivo **`index.html`** será atualizado/gerado automaticamente. Basta abri-lo no seu navegador favorito.

## Funcionalidades do Mapa Gerado
- **Categorização visual:** Os marcadores possuem cores diferentes dependendo da operadora (ex: CLARO, VIVO, TIM).
- **Pop-ups:** Ao clicar em um marcador da antena, um card será aberto contendo a foto otimizada e informações de localização, infraestrutura, tecnologias suportadas e faixa (MHz).
- **Controles interativos:** Funcionalidades de tela cheia, buscar endereços e mini-mapa incorporados.
