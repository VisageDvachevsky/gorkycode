import L from 'leaflet'

let configured = false

const configureLeafletIcons = () => {
  if (configured) return

  delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: () => void })._getIconUrl

  L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  })

  configured = true
}

configureLeafletIcons()

const defaultOptions = L.Icon.Default.prototype.options as L.IconOptions

export const defaultMarkerIcon = L.icon(defaultOptions)

export const coffeeMarkerIcon = L.divIcon({
  html: `<div class="coffee-marker" style="
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
    border-radius: 50% 50% 50% 0;
    transform: rotate(-45deg);
    border: 3px solid white;
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
  ">
    <span style="transform: rotate(45deg); font-size: 22px;">☕</span>
  </div>`,
  className: '',
  iconSize: [40, 40],
  iconAnchor: [20, 40],
  popupAnchor: [0, -40],
})

export default L
