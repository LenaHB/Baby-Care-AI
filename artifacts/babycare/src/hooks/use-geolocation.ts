import { useState, useEffect } from "react";

interface LocationState {
  lat: number | null;
  lng: number | null;
  error: string | null;
  loading: boolean;
}

export function useGeolocation() {
  const [state, setState] = useState<LocationState>({
    lat: null,
    lng: null,
    error: null,
    loading: true,
  });

  useEffect(() => {
    if (!navigator.geolocation) {
      setState((prev) => ({ ...prev, loading: false, error: "Geolocation not supported" }));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setState({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          error: null,
          loading: false,
        });
      },
      (err) => {
        setState((prev) => ({ ...prev, loading: false, error: err.message }));
      }
    );
  }, []);

  return state;
}
