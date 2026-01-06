import io
import folium
from PyQt6.QtWebEngineWidgets import QWebEngineView

class MapWidget(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #e5e7eb; border-radius: 6px;")
        self.update_map(35.5438, 129.4276)

    def update_map(self, lat, lng):
        # folium으로 지도 생성
        m = folium.Map(location=[lat, lng], zoom_start=15, control_scale=True)
        folium.Marker(
            [lat, lng],
            popup=f"Lat: {lat:.4f}<br>Lng: {lng:.4f}",
            tooltip="Current Position",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)
        
        # 지도를 HTML 데이터로 변환하여 QWebEngineView에 로드
        data = io.BytesIO()
        m.save(data, close_file=False)
        self.setHtml(data.getvalue().decode())