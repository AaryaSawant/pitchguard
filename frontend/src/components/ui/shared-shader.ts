import { liquidMetalFragmentShader, ShaderMount } from "@paper-design/shaders";

// --- Shared WebGL Shader Singleton ---
// This completely bypasses the browser's WebGL context limit (usually 8 or 16)
// by rendering the complex shader ONCE, and copying it to 2D canvases.

// biome-ignore lint/suspicious/noExplicitAny: External library without types
export let sharedShaderMount: any = null;
export let sharedCanvas: HTMLCanvasElement | null = null;
export const activeSharedCards = new Set<() => void>();
let renderLoopStarted = false;

export function initSharedShader() {
  if (sharedShaderMount) return;
  const container = document.createElement("div");
  // A high enough resolution for the border texture
  container.style.width = "512px";
  container.style.height = "512px";
  container.style.position = "fixed";
  container.style.top = "-9999px";
  container.style.left = "-9999px";
  container.style.opacity = "0";
  container.style.pointerEvents = "none";
  document.body.appendChild(container);

  sharedShaderMount = new ShaderMount(
    container,
    liquidMetalFragmentShader,
    {
      u_repetition: 4,
      u_softness: 0.5,
      u_shiftRed: 0.3,
      u_shiftBlue: 0.3,
      u_distortion: 0,
      u_contour: 0,
      u_angle: 45,
      u_scale: 8,
      u_shape: 0,
      u_offsetX: 0.1,
      u_offsetY: -0.1,
    },
    undefined,
    0.6,
  );

  sharedCanvas = container.querySelector("canvas");

  if (!renderLoopStarted) {
    renderLoopStarted = true;
    function renderLoop() {
      activeSharedCards.forEach(renderFn => renderFn());
      requestAnimationFrame(renderLoop);
    }
    requestAnimationFrame(renderLoop);
  }
}

export function setSharedShaderSpeed(speed: number) {
  if (sharedShaderMount?.setSpeed) {
    sharedShaderMount.setSpeed(speed);
  }
}
