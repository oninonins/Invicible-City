"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Fix for default marker icons in Leaflet with Next.js
const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

interface Facility {
  id: number;
  name: string;
  facility_type: string;
  lat: number;
  lng: number;
}

export default function Map() {
  const [facilities, setFacilities] = useState<Facility[]>([]);

  useEffect(() => {
    // Fetch facilities from API
    const fetchFacilities = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/facilities`);
        if (response.ok) {
          const data = await response.json();
          setFacilities(data);
        }
      } catch (error) {
        console.error("Failed to fetch facilities:", error);
      }
    };
    
    fetchFacilities();
  }, []);

  return (
    <div className="h-[calc(100vh-12rem)] w-full rounded-xl overflow-hidden border shadow-sm z-0">
      <MapContainer 
        center={[-6.200000, 106.816666]} // Default to Jakarta
        zoom={11} 
        scrollWheelZoom={true}
        style={{ height: "100%", width: "100%", zIndex: 0 }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {facilities.map((fac) => (
          <Marker key={fac.id} position={[fac.lat, fac.lng]} icon={icon}>
            <Popup>
              <strong>{fac.name}</strong><br />
              Type: {fac.facility_type}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
