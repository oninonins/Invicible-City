"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, GeoJSON, LayersControl, LayerGroup, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { School, Hospital, Stethoscope, Bus, Trees, Building2, MapPin } from "lucide-react";
import { renderToString } from "react-dom/server";

// Configuration-based styling for civic tech map
const MAP_CONFIG = {
  boundaryStyle: {
    color: "#2563eb", // Primary blue
    weight: 2.5,
    dashArray: "6, 6",
    fillColor: "#3b82f6",
    fillOpacity: 0.04,
  },
  districtStyle: {
    color: "#475569", // Slate-600
    weight: 1.2,
    dashArray: "3, 3",
    fillColor: "transparent",
  },
  facilityTypes: {
    School: { name: "School", color: "#2563eb", icon: <School size={15} color="white" /> },
    Hospital: { name: "Hospital", color: "#dc2626", icon: <Hospital size={15} color="white" /> },
    Clinic: { name: "Clinic", color: "#e11d48", icon: <Stethoscope size={15} color="white" /> },
    BusStop: { name: "Bus Stop", color: "#d97706", icon: <Bus size={15} color="white" /> },
    Park: { name: "Park", color: "#059669", icon: <Trees size={15} color="white" /> },
    Healthcare: { name: "Healthcare", color: "#dc2626", icon: <Hospital size={15} color="white" /> },
    Transport: { name: "Transport", color: "#d97706", icon: <Bus size={15} color="white" /> },
    default: { name: "Facility", color: "#64748b", icon: <Building2 size={15} color="white" /> }
  }
};

// Normalize facility type helper
export const normalizeFacilityType = (type: string): string => {
  if (!type) return "default";
  const cleaned = type.replace(/\s+/g, "");
  if (cleaned === "BusStop" || cleaned === "Bus Stop") return "BusStop";
  if (cleaned === "School") return "School";
  if (cleaned === "Hospital") return "Hospital";
  if (cleaned === "Clinic") return "Clinic";
  if (cleaned === "Park") return "Park";
  if (cleaned === "Healthcare") return "Healthcare";
  if (cleaned === "Transport") return "Transport";
  return "default";
};

// Create custom Leaflet DivIcon
const createCustomIcon = (rawType: string) => {
  const normKey = normalizeFacilityType(rawType);
  const config = MAP_CONFIG.facilityTypes[normKey as keyof typeof MAP_CONFIG.facilityTypes] || MAP_CONFIG.facilityTypes.default;
  
  const iconHtml = renderToString(
    <div style={{
      backgroundColor: config.color,
      width: '28px',
      height: '28px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: '50%',
      boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
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

// Auto-fit bounds component
function BoundsHelper({ boundary, facilities }: { boundary: unknown; facilities: Facility[] }) {
  const map = useMap();
  
  useEffect(() => {
    if (boundary && (boundary as { features?: unknown[] }).features && (boundary as { features: unknown[] }).features.length > 0) {
      try {
        const geoJsonLayer = L.geoJSON(boundary as GeoJSON.GeoJsonObject);
        const bounds = geoJsonLayer.getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
          return;
        }
      } catch (e) {
        console.error("Failed to fit boundary bounds", e);
      }
    }

    if (facilities && facilities.length > 0) {
      try {
        const points = facilities.map(f => [f.lat, f.lng] as [number, number]);
        const bounds = L.latLngBounds(points);
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
        }
      } catch (e) {
        console.error("Failed to fit facility bounds", e);
      }
    }
  }, [boundary, facilities, map]);

  return null;
}

export interface Facility {
  id: number;
  name: string;
  facility_type: string;
  lat: number;
  lng: number;
  district_name?: string;
}

interface MapProps {
  facilities: Facility[];
  boundary?: Record<string, unknown> | null;
  districts?: Record<string, unknown> | null;
  loading?: boolean;
  activeFilter?: string; // "ALL" or specific type like "School"
  onSelectFacility?: (facility: Facility) => void;
}

export default function Map({ facilities, boundary, districts, loading, activeFilter = "ALL", onSelectFacility }: MapProps) {
  // Filter facilities based on active category
  const filteredFacilities = facilities.filter(f => {
    if (!activeFilter || activeFilter === "ALL") return true;
    const norm = normalizeFacilityType(f.facility_type);
    const targetNorm = normalizeFacilityType(activeFilter);
    return norm === targetNorm;
  });

  return (
    <div className="h-full w-full rounded-xl overflow-hidden border border-border shadow-sm z-0 relative bg-muted/10">
      {loading && (
        <div className="absolute inset-0 z-[1000] bg-background/60 backdrop-blur-sm flex flex-col items-center justify-center">
          <div className="animate-spin rounded-full h-9 w-9 border-b-2 border-primary mb-2"></div>
          <span className="text-xs font-medium text-muted-foreground">Loading spatial layers...</span>
        </div>
      )}

      {/* Explicit No Data overlay if empty and not loading */}
      {!loading && facilities.length === 0 && !boundary && (
        <div className="absolute inset-0 z-[900] bg-background/80 backdrop-blur-sm flex flex-col items-center justify-center p-6 text-center">
          <MapPin className="h-10 w-10 text-muted-foreground mb-2" />
          <h4 className="font-semibold text-lg">No Spatial Data Mapped</h4>
          <p className="text-sm text-muted-foreground max-w-sm mt-1">
            Facilities and boundary geometries have not been imported for this location yet.
          </p>
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
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        
        {/* Bounds auto-fitter */}
        <BoundsHelper boundary={boundary} facilities={filteredFacilities} />

        <LayersControl position="topright">
          {/* Administrative Boundary Layers */}
          {boundary && (
            <LayersControl.Overlay checked name="City Boundary">
              <LayerGroup>
                <GeoJSON data={(boundary as unknown) as GeoJSON.GeoJsonObject} pathOptions={MAP_CONFIG.boundaryStyle} />
              </LayerGroup>
            </LayersControl.Overlay>
          )}
          
          {districts && (
            <LayersControl.Overlay checked name="District Subdivisions">
              <LayerGroup>
                <GeoJSON 
                  data={(districts as unknown) as GeoJSON.GeoJsonObject} 
                  pathOptions={MAP_CONFIG.districtStyle} 
                  onEachFeature={(feature: GeoJSON.Feature, layer: L.Layer) => {
                    if (feature.properties && feature.properties.name) {
                      layer.bindTooltip(feature.properties.name, { 
                        permanent: false, 
                        direction: 'center',
                        className: 'district-tooltip'
                      });
                    }
                  }}
                />
              </LayerGroup>
            </LayersControl.Overlay>
          )}

          {/* Facility Layer Group with Clustering */}
          <LayersControl.Overlay checked name="Public Facilities">
            <MarkerClusterGroup
              chunkedLoading
              maxClusterRadius={40}
              spiderfyOnMaxZoom={true}
            >
              {filteredFacilities.map((fac) => {
                const normKey = normalizeFacilityType(fac.facility_type);
                const config = MAP_CONFIG.facilityTypes[normKey as keyof typeof MAP_CONFIG.facilityTypes] || MAP_CONFIG.facilityTypes.default;
                
                return (
                  <Marker 
                    key={fac.id} 
                    position={[fac.lat, fac.lng]} 
                    icon={createCustomIcon(fac.facility_type)}
                    eventHandlers={{
                      click: () => onSelectFacility?.(fac)
                    }}
                  >
                    <Popup className="custom-popup">
                      <div className="p-2 space-y-1 max-w-xs">
                        <div className="font-bold text-sm tracking-tight">{fac.name}</div>
                        <div className="flex items-center gap-1.5 pt-1">
                          <span 
                            className="inline-block w-2.5 h-2.5 rounded-full" 
                            style={{ backgroundColor: config.color }}
                          />
                          <span className="text-xs font-semibold text-foreground uppercase tracking-wider">
                            {fac.facility_type}
                          </span>
                        </div>
                        {fac.district_name && (
                          <div className="text-xs text-muted-foreground">
                            District: {fac.district_name}
                          </div>
                        )}
                        <div className="text-[10px] font-mono text-muted-foreground pt-1">
                          {fac.lat.toFixed(5)}, {fac.lng.toFixed(5)}
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}
            </MarkerClusterGroup>
          </LayersControl.Overlay>
        </LayersControl>
      </MapContainer>
    </div>
  );
}
