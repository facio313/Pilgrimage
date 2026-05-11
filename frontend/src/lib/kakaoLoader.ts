declare global {
  interface Window {
    kakao: any;
  }
}

let loaderPromise: Promise<any> | null = null;

export function loadKakao(): Promise<any> {
  if (loaderPromise) return loaderPromise;

  const appKey = import.meta.env.VITE_KAKAO_JS_KEY;
  if (!appKey) {
    return Promise.reject(new Error('VITE_KAKAO_JS_KEY is not set'));
  }

  loaderPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.async = true;
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${appKey}&autoload=false&libraries=services`;
    script.addEventListener('load', () => {
      window.kakao.maps.load(() => resolve(window.kakao));
    });
    script.addEventListener('error', () => {
      loaderPromise = null;
      reject(new Error('Failed to load Kakao Maps SDK'));
    });
    document.head.appendChild(script);
  });

  return loaderPromise;
}
