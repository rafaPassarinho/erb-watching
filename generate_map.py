import folium
import json
from folium import plugins
from pathlib import Path
import random

def get_operator_color(operadora):
    """Define cores específicas por operadora."""
    colors = {
        'CLARO': 'red',
        'VIVO': 'purple',
        'TIM': 'blue',
    }
    return colors.get(operadora, 'gray')  # Cor padrão para operadoras desconhecidas

def generate_erb_map(data_json_path='data.json', output_html='index.html'):
    """Gera mapa interativo com Folium e salva como index.html."""

    # carregar dados
    with open(data_json_path, 'r', encoding='utf-8') as f:
        erb_data = json.load(f)

    # filtrar apenas ERBs com foto
    erbs_with_photos = [erb for erb in erb_data if erb['tem_foto']]

    if not erbs_with_photos:
        print("Nenhuma ERB com foto encontrada.")
        return
    
    # centro do mapa (média das coordenadas)
    center_lat = sum(erb['latitude'] for erb in erbs_with_photos) / len(erbs_with_photos)
    center_lon = sum(erb['longitude'] for erb in erbs_with_photos) / len(erbs_with_photos)

    # criar mapa base
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        min_zoom=11, # Impede de afastar o mapa para o mundo inteiro
        max_zoom=19, # Limitar o zoom in também, caso precise
        tiles=None # removemos tiles padrão
    )

    # adicionar tile layer do OpenStreetMap (semântico e limpo)
    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        name='Mapa Claro'
    ).add_to(m)

    # agrupar marcadores por operadora
    operator_groups = {}
    for operadora in ['CLARO', 'VIVO', 'TIM']:
        operator_groups[operadora] = folium.FeatureGroup(name=operadora)

    # adicionar marcadores ao mapa
    for erb in erbs_with_photos:
        # Criar conteúdo do popup HTML
        popup_html = f"""
        <div class="erb-popup">
            <h3>ERB #{erb['num_estacao']}</h3>
            <div class="erb-info">
                <p><strong>Operadora:</strong> {erb['operadora']}</p>
                <p><strong>Tecnologias:</strong> {erb['tecnologias']}</p>
                <p><strong>Faixas:</strong> {erb['faixa']} MHz</p>
                <p><strong>Infraestrutura:</strong> {erb['class_infra_fisica']}</p>
                <p><strong>Localização:</strong><br>
                {erb['logradouro']}<br>
                {erb['bairro']}, {erb['municipio']} - {erb['sigla_uf']}</p>
                <img src="{erb['foto_path']}" alt="Foto ERB {erb['num_estacao']}" 
                     style="width:100%; max-width:280px; border-radius:5px; margin-top:10px;"
                     onerror="this.style.display='none'">
            </div>
        </div>
        """
        
        # Criar marcador com ícone personalizado
        icon_color = get_operator_color(erb['operadora'])
        
        folium.Marker(
            location=[erb['latitude'], erb['longitude']],
            popup=folium.Popup(popup_html, max_width=300, min_width=200),
            tooltip=f"{erb['operadora']} - ERB #{erb['num_estacao']}",
            icon=folium.Icon(color=icon_color, icon='signal', prefix='fa')
        ).add_to(operator_groups[erb['operadora']])

    # adicionar grupos de operadoras ao mapa
    for group in operator_groups.values():
        group.add_to(m)

    # adicionar controle de camadas
    #folium.LayerControl().add_to(m)

    # adicionar mini mapa
    minimap = plugins.MiniMap(toggle_display=True)
    m.add_child(minimap)

    # adicionar botão de localização
    #plugins.Geocoder().add_to(m)

    # adicionar fullscreen
    plugins.Fullscreen().add_to(m)

    # salvar mapa como index.html
    m.save(output_html)

    # adicionar estilos personalizados ao HTML gerado
    add_custom_styles(output_html)

    print(f"Mapa gerado com sucesso: {output_html}")
    print(f"Total de ERBs com foto: {len(erbs_with_photos)}")

def add_custom_styles(html_path):
    """Adiciona estilos CSS personalizados ao HTML do Folium."""

    # Sua fonte do Google Fonts
    google_fonts_link = """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Rubik+Glitch&display=swap" rel="stylesheet">
    """

    # Novo bloco de texto a ser inserido abaixo do mapa
    infra_info_html = """
    <div class="infra-info-container">
        <h2>Classificações de Infraestruturas Físicas de ERBs</h2>
        <p><strong>COW:</strong> Cell on Wheels (Célula sobre Rodas) é uma ERB montada sobre uma plataforma que pode ser deslocada para locais temporários ou áreas de grande demanda. É frequentemente usada em grandes eventos, como shows ou em situações de emergência.</p>
        <p><strong>Fastsite:</strong> ERB de rápida instalação em áreas urbanas. São usadas para aumentar a capacidade da rede em locais movimentados, como estações de metrô ou pontos de ônibus.</p>
        <p><strong>Greenfield:</strong> ERB instalada em áreas que não têm infraestrutura de telecomunicações pré-existente. Essas áreas costumam ser locais de desenvolvimento ou construções recentes.</p>
        <p><strong>Harmonizada:</strong> ERB que combina tecnologias de diferentes provedores de serviços de telecomunicações. Geralmente, elas suportam várias bandas de frequência e tecnologias, incluindo 2G, 3G e 4G.</p>
        <p><strong>Indoor:</strong> ERB utilizada para fornecer cobertura dentro de prédios, como escritórios, shoppings e aeroportos.</p>
        <p><strong>Outdoor:</strong> ERB utilizada para fornecer cobertura em áreas externas, como ruas, parques e praças.</p>
        <p><strong>Ran Sharing:</strong> ERB compartilhada entre diferentes provedores de serviços de telecomunicações. É uma solução mais econômica do que a instalação de várias ERBs separadas em uma área.</p>
        <p><strong>Rooftop:</strong> ERB instalada no topo de prédios. É frequentemente usada em áreas urbanas densamente povoadas.</p>
        <p><strong>SmallCell:</strong> ERB de pequeno porte, usada para fornecer cobertura em áreas de baixa densidade de tráfego, como estações de trem ou áreas rurais.</p>
        <p><strong>Streetlevel:</strong> ERB instalada em postes ou caixas de eletricidade ao nível da rua. É usada para fornecer cobertura em áreas urbanas movimentadas.</p>
    </div>
    """

    custom_css = f"""
    {google_fonts_link}
    <style>
        /* Fonte principal e estilos gerais da página */
        body {{
            margin: 0;
            padding: 20px 0;
            font-family: "Rubik Glitch", system-ui; /* Para mudar a fonte principal, altere aqui */
            background-image: url('processed_photos/684594340.jpg');
            background-size: 300px 200px;
            background-repeat: repeat;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }}

        .custom-header {{
            margin-bottom: 20px;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px 40px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            text-align: center;
        }}
        
        .custom-header h1 {{
            margin: 0;
            font-size: 32px;
            color: #2c3e50;
            font-weight: 700;
        }}

        /* O mapa inteiro é sobrescrito para Segoe UI */
        .folium-map {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
            width: 80vw !important;
            height: 60vh !important;
            max-width: 1200px;
            max-height: 700px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            border: 4px solid white;
            position: relative !important; 
            margin-bottom: 30px;
        }}
        
        .page-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
            max-width: 1200px;
        }}

        .infra-info-container {{
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            width: 80vw;
            max-width: 1200px;
            color: #333;
            line-height: 1.6;
            margin-bottom: 40px;
        }}

        .infra-info-container h2 {{
            margin-top: 0;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}

        .infra-info-container p strong {{
            color: #e74c3c;
            font-size: 1.1em;
        }}

        .erb-popup {{
            min-width: 350px;
        }}
        
        .erb-popup h3 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        
        .erb-info {{
            line-height: 1.6;
        }}
        
        .erb-info img {{
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        /* Os popups de dentro do mapa devem explicitamente ser Segoe UI */
        .leaflet-popup-content-wrapper {{
            border-radius: 10px;
            box-shadow: 0 3px 15px rgba(0,0,0,0.2);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        }}
    </style>
    """
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Inserir CSS, Fontes, Header acima do mapa, e Legendas abaixo do mapa
    
    # 1. Coloca tudo que fica no head
    content = content.replace('</head>', f'{custom_css}</head>')
    
    # 2. Folium insere o mapa direto no body. Vamos criar wrappers usando replace.
    # Envolvemos o <body> para inserir o título antes e a caixa de infos depois do mapa.
    content = content.replace('<body>', 
                              '<body>\n<div class="page-wrapper">\n<div class="custom-header"><h1>ERB Watching</h1></div>')
    
    content = content.replace('</body>', 
                              f'\n{infra_info_html}\n</div>\n</body>')
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    generate_erb_map()