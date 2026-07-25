"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, GeoJSON, LayersControl, LayerGroup, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { Building2, HeartPulse, Bus } from "lucide-react";
import { renderToString } from "react-dom/server";

// Configuration-based styling
const MAP_CONFIG = {
  boundaryStyle: {
    color: "#3b82f6", // Blue
    weight: 2,
    dashArray: "5, 5",
    fillColor: "#3b82f6",
    fillOpacity: 0.05,
  },
  districtStyle: {
    color: "#64748b", // Slate
    weight: 1,
    dashArray: "3, 3",
    fillColor: "transparent",
  },
  facilityTypes: {
    School: { color: "#3b82f6", icon: <Building2 size={16} color="white" /> },
    Healthcare: { color: "#ef4444", icon: <HeartPulse size={16} color="white" /> },
    Transport: { color: "#eab308", icon: <Bus size={16} color="white" /> },
    default: { color: "#6b7280", icon: <div className="w-2 h-2 rounded-full bg-white" /> }
  }
};

// Create custom DivIcon for markers
const createCustomIcon = (type: string) => {
  const config = MAP_CONFIG.facilityTypes[type as keyof typeof MAP_CONFIG.facilityTypes] || MAP_CONFIG.facilityTypes.default;
  
  const iconHtml = renderToString(
    <div style={{
      backgroundColor: config.color,
      width: '28px',
      height: '28px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: '50%',
      boxShadow: '0 2px 5px rgba(0,0,0,0.3)',
      border: '2px solid white'
    }}>
      {config.icon}
    </div>
  );

  return L.divIcon({
    html: iconHtml,
    className: 'custom-leaflet-icon',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

// Component to handle auto-panning
function BoundsHelper({ boundary }: { boundary: Record<string, unknown> | null | undefined }) {
  const map = useMap();
  
  useEffect(() => {
    if (boundary && (boundary as Record<string, unknown[]>).features && (boundary as Record<string, unknown[]>).features.length > 0) {
      try {
        const geoJsonLayer = L.geoJSON(boundary);
        const bounds = geoJsonLayer.getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
        }
      } catch (e) {
        console.error("Failed to fit bounds", e);
      }
    }
  }, [boundary, map]);

  return null;
}

interface Facility {
  id: number;
  name: string;
  facility_type: string;
  lat: number;
  lng: number;
}

interface MapProps {
  facilities: Facility[];
  boundary?: Record<string, unknown> | null;
  districts?: Record<string, unknown> | null;
  loading?: boolean;
}

export default function Map({ facilities, boundary, districts, loading }: MapProps) {
  return (
    <div className="h-[calc(100vh-12rem)] w-full rounded-xl overflow-hidden border shadow-sm z-0 relative">
      {loading && (
        <div className="absolute inset-0 z-[1000] bg-background/50 backdrop-blur-sm flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      )}
      
      <MapContainer 
        center={[-6.200000, 106.816666]} 
        zoom={11} 
        scrollWheelZoom={true}
        style={{ height: "100%", width: "100%", zIndex: 0 }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png" // Sleeker map style
        />
        
        {/* Bounds auto-fitter */}
        <BoundsHelper boundary={boundary} />

        <LayersControl position="topright">
          {/* Administrative Layers */}
          <LayersControl.Overlay checked name="City Boundary">
            <LayerGroup>
              {boundary && (
                <GeoJSON data={boundary} pathOptions={MAP_CONFIG.boundaryStyle} />
              )}
            </LayerGroup>
          </LayersControl.Overlay>
          
          <LayersControl.Overlay checked name="Districts">
            <LayerGroup>
              {districts && (
                <GeoJSON 
                  data={districts} 
                  pathOptions={MAP_CONFIG.districtStyle} 
                  onEachFeature={(feature, layer) => {
                    if (feature.properties && feature.properties.name) {
                      layer.bindTooltip(feature.properties.name, { permanent: false, direction: 'center' });
                    }
                  }}
                />
              )}
            </LayerGroup>
          </LayersControl.Overlay>

          {/* Facility Layers */}
          {Object.keys(MAP_CONFIG.facilityTypes).filter(t => t !== 'default').map((type) => {
            const facsForType = facilities.filter(f => f.facility_type === type);
            if (facsForType.length === 0) return null;
            
            return (
              <LayersControl.Overlay checked name={type} key={type}>
                <MarkerClusterGroup
                  chunkedLoading
                  maxClusterRadius={40}
                  spiderfyOnMaxZoom={true}
                >
                  {facsForType.map((fac) => (
                    <Marker 
                      key={fac.id} 
                      position={[fac.lat, fac.lng]} 
                      icon={createCustomIcon(fac.facility_type)}
                    >
                      <Popup className="custom-popup">
                        <div className="p-1">
                          <div className="font-bold text-sm mb-1">{fac.name}</div>
                          <div className="text-xs text-muted-foreground flex items-center gap-1">
                            <span className="inline-block w-2 h-2 rounded-full" 
                                  style={{backgroundColor: MAP_CONFIG.facilityTypes[fac.facility_type as keyof typeof MAP_CONFIG.facilityTypes]?.color || '#000'}}>
                            </span>
                            {fac.facility_type}
                          </div>
                        </div>
                      </Popup>
                    </Marker>
                  ))}
                </MarkerClusterGroup>
              </LayersControl.Overlay>
            );
          })}
        </LayersControl>
      </MapContainer>
    </div>
  );
}
