import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { MapPin, Navigation, Compass, AlertCircle } from "lucide-react";
import { useLang } from "./LanguageContext";

// Modern SVG DivIcon for crisp, dependency-free marker rendering
const createCustomPinIcon = () => {
  return L.divIcon({
    className: "custom-map-pin-wrapper",
    html: `
      <div style="
        position: relative;
        transform: translate(-50%, -100%);
        cursor: grab;
        display: flex;
        flex-direction: column;
        align-items: center;
      ">
        <div style="
          background: linear-gradient(135deg, #16a34a, #15803d);
          color: white;
          width: 38px;
          height: 38px;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 12px rgba(22, 163, 74, 0.45);
          border: 2px solid #ffffff;
        ">
          <span style="transform: rotate(45deg); font-size: 16px; line-height: 1;">🌱</span>
        </div>
        <div style="
          width: 14px;
          height: 6px;
          background: rgba(0,0,0,0.25);
          border-radius: 50%;
          margin-top: 2px;
          filter: blur(1px);
        "></div>
      </div>
    `,
    iconSize: [38, 44],
    iconAnchor: [19, 44],
  });
};

export default function InteractiveLocationMap({
  latitude,
  longitude,
  locationName,
  onChangeLocation,
  onLocateUser,
  isLocating = false,
  error = "",
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);
  const [mapError, setMapError] = useState("");
  const [,, t] = useLang();

  const googleApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

  // Fallback / default center (Central India / Pune if not specified)
  const effectiveLat = typeof latitude === "number" && !isNaN(latitude) ? latitude : 20.5937;
  const effectiveLon = typeof longitude === "number" && !isNaN(longitude) ? longitude : 78.9629;
  const hasCoordinates = typeof latitude === "number" && !isNaN(latitude) && typeof longitude === "number" && !isNaN(longitude);

  useEffect(() => {
    // If Google Maps API key is configured, dynamically initialize Google Maps
    if (googleApiKey) {
      // Structure code to load Google Maps script dynamically
      if (!window.google || !window.google.maps) {
        const scriptId = "google-maps-sdk";
        if (!document.getElementById(scriptId)) {
          const script = document.createElement("script");
          script.id = scriptId;
          script.src = `https://maps.googleapis.com/maps/api/js?key=${googleApiKey}`;
          script.async = true;
          script.onload = () => initGoogleMap();
          script.onerror = () => {
            console.warn("Failed to load Google Maps SDK. Falling back to OpenStreetMap.");
            initLeafletMap();
          };
          document.head.appendChild(script);
        }
      } else {
        initGoogleMap();
      }
      return;
    }

    // Default to interactive Leaflet with OpenStreetMap
    initLeafletMap();

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [googleApiKey]);

  const initGoogleMap = () => {
    if (!mapContainerRef.current || !window.google || !window.google.maps) return;
    try {
      const center = { lat: effectiveLat, lng: effectiveLon };
      const map = new window.google.maps.Map(mapContainerRef.current, {
        center,
        zoom: hasCoordinates ? 13 : 5,
        mapTypeId: "hybrid",
        streetViewControl: false,
        fullscreenControl: false,
      });

      const marker = new window.google.maps.Marker({
        position: center,
        map: hasCoordinates ? map : null,
        draggable: true,
        animation: window.google.maps.Animation.DROP,
        title: locationName || "Farm Location",
      });

      map.addListener("click", (e) => {
        const newLat = e.latLng.lat();
        const newLng = e.latLng.lng();
        marker.setPosition({ lat: newLat, lng: newLng });
        marker.setMap(map);
        onChangeLocation(newLat, newLng, "map_click");
      });

      marker.addListener("dragend", (e) => {
        const newLat = e.latLng.lat();
        const newLng = e.latLng.lng();
        onChangeLocation(newLat, newLng, "map_click");
      });

      mapInstanceRef.current = map;
      markerRef.current = marker;
    } catch (err) {
      console.warn("Google Maps init failed, falling back to Leaflet:", err);
      initLeafletMap();
    }
  };

  const initLeafletMap = () => {
    if (!mapContainerRef.current) return;

    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    try {
      const map = L.map(mapContainerRef.current, {
        center: [effectiveLat, effectiveLon],
        zoom: hasCoordinates ? 13 : 5,
        zoomControl: true,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      const customIcon = createCustomPinIcon();

      if (hasCoordinates) {
        const marker = L.marker([effectiveLat, effectiveLon], {
          icon: customIcon,
          draggable: true,
        }).addTo(map);

        marker.on("dragend", (e) => {
          const { lat, lng } = e.target.getLatLng();
          onChangeLocation(lat, lng, "map_click");
        });

        markerRef.current = marker;
      }

      map.on("click", (e) => {
        const { lat, lng } = e.latlng;
        if (!markerRef.current) {
          const marker = L.marker([lat, lng], {
            icon: customIcon,
            draggable: true,
          }).addTo(map);

          marker.on("dragend", (event) => {
            const pos = event.target.getLatLng();
            onChangeLocation(pos.lat, pos.lng, "map_click");
          });

          markerRef.current = marker;
        } else {
          markerRef.current.setLatLng([lat, lng]);
        }
        onChangeLocation(lat, lng, "map_click");
      });

      mapInstanceRef.current = map;
    } catch (err) {
      setMapError("Unable to render interactive map. You can still enter coordinates or use GPS detection.");
    }
  };

  // Sync marker and view when coordinates change from outside (GPS or search)
  useEffect(() => {
    if (!hasCoordinates || !mapInstanceRef.current) return;

    // Google Maps sync
    if (googleApiKey && window.google && window.google.maps) {
      const pos = { lat: latitude, lng: longitude };
      if (markerRef.current) {
        markerRef.current.setPosition(pos);
        markerRef.current.setMap(mapInstanceRef.current);
      }
      mapInstanceRef.current.panTo(pos);
      return;
    }

    // Leaflet sync
    const map = mapInstanceRef.current;
    if (map && map.setView) {
      map.setView([latitude, longitude], 13);
      if (markerRef.current) {
        markerRef.current.setLatLng([latitude, longitude]);
      } else {
        const marker = L.marker([latitude, longitude], {
          icon: createCustomPinIcon(),
          draggable: true,
        }).addTo(map);

        marker.on("dragend", (e) => {
          const { lat, lng } = e.target.getLatLng();
          onChangeLocation(lat, lng, "map_click");
        });

        markerRef.current = marker;
      }
    }
  }, [latitude, longitude, googleApiKey]);

  return (
    <div className="interactiveMapCard">
      <div className="mapToolbar">
        <div className="mapTitle">
          <MapPin size={18} color="#16a34a"/>
          <span><strong>{t.farmLocationPin || "Farm Location Pin"}</strong> {hasCoordinates ? `(${latitude.toFixed(4)}, ${longitude.toFixed(4)})` : (t.clickToPlacePin || "(Click to place pin)")}</span>
        </div>

        <div className="mapToolbarActions">
          {onLocateUser && (
            <button
              type="button"
              className="button secondary locateMeBtn"
              onClick={onLocateUser}
              disabled={isLocating}
              title="Detect precise location using browser GPS"
            >
              <Navigation size={15} className={isLocating ? "spin" : ""}/>
              {isLocating ? (t.locating || "Locating...") : (t.useCurrentLocation || "Use My Current Location")}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mapAlert error">
          <AlertCircle size={16}/>
          <span>{error}</span>
        </div>
      )}

      {mapError ? (
        <div className="mapAlert warning">
          <AlertCircle size={16}/>
          <span>{mapError}</span>
        </div>
      ) : (
        <div className="mapContainerWrapper">
          <div ref={mapContainerRef} className="mapContainer" style={{ height: 280, width: "100%", borderRadius: "8px" }} />
          <div className="mapInstructionHint">
            💡 <em>{t.mapInstruction || "Click anywhere on the map or drag the pin to set your exact field location."}</em>
          </div>
        </div>
      )}

      {hasCoordinates && locationName && (
        <div className="mapResolvedAddress">
          <strong>{t.identifiedArea || "Identified Area"}:</strong> {locationName}
        </div>
      )}
    </div>
  );
}
