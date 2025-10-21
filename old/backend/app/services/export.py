from datetime import datetime
from typing import List
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from app.models.schemas import POIInRoute


class ExportService:
    @staticmethod
    def generate_gpx(route: List[POIInRoute], route_name: str = "AI-Tourist Route") -> str:
        gpx = Element('gpx', {
            'version': '1.1',
            'creator': 'AI-Tourist',
            'xmlns': 'http://www.topografix.com/GPX/1/1',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': 'http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd',
        })
        
        metadata = SubElement(gpx, 'metadata')
        SubElement(metadata, 'name').text = route_name
        SubElement(metadata, 'time').text = datetime.utcnow().isoformat() + 'Z'
        
        trk = SubElement(gpx, 'trk')
        SubElement(trk, 'name').text = route_name
        trkseg = SubElement(trk, 'trkseg')
        
        for poi in route:
            trkpt = SubElement(trkseg, 'trkpt', {
                'lat': str(poi.lat),
                'lon': str(poi.lon),
            })
            SubElement(trkpt, 'name').text = poi.name
            SubElement(trkpt, 'desc').text = poi.why
            SubElement(trkpt, 'time').text = poi.arrival_time.isoformat() + 'Z'
        
        for poi in route:
            wpt = SubElement(gpx, 'wpt', {
                'lat': str(poi.lat),
                'lon': str(poi.lon),
            })
            SubElement(wpt, 'name').text = f"{poi.order}. {poi.name}"
            SubElement(wpt, 'desc').text = poi.why
            if poi.tip:
                SubElement(wpt, 'cmt').text = poi.tip
            SubElement(wpt, 'time').text = poi.arrival_time.isoformat() + 'Z'
        
        xml_str = tostring(gpx, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ')
    
    @staticmethod
    def generate_share_link(route_id: str, base_url: str = "https://aitourist.app") -> str:
        return f"{base_url}/route/{route_id}"


export_service = ExportService()