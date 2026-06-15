import { useEffect, useRef } from "react";
import gsap from "gsap";

export default function CustomCursor() {
  const bigBallRef = useRef<HTMLDivElement>(null);
  const smallBallRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Hide default cursor globally
    const style = document.createElement("style");
    style.innerHTML = `
      * {
        cursor: none !important;
      }
    `;
    document.head.appendChild(style);

    const onMouseMove = (e: MouseEvent) => {
      gsap.to(bigBallRef.current, {
        duration: 0.4,
        x: e.clientX - 15,
        y: e.clientY - 15
      });
      gsap.to(smallBallRef.current, {
        duration: 0.1,
        x: e.clientX - 5,
        y: e.clientY - 7
      });
    };

    const onMouseHover = () => {
      gsap.to(bigBallRef.current, {
        duration: 0.3,
        scale: 4
      });
    };

    const onMouseHoverOut = () => {
      gsap.to(bigBallRef.current, {
        duration: 0.3,
        scale: 1
      });
    };

    // Use event delegation for hover states
    const handleMouseOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName.toLowerCase() === "a" ||
        target.tagName.toLowerCase() === "button" ||
        target.closest("a") ||
        target.closest("button") ||
        target.classList.contains("hoverable")
      ) {
        onMouseHover();
      }
    };

    const handleMouseOut = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName.toLowerCase() === "a" ||
        target.tagName.toLowerCase() === "button" ||
        target.closest("a") ||
        target.closest("button") ||
        target.classList.contains("hoverable")
      ) {
        onMouseHoverOut();
      }
    };

    document.body.addEventListener("mousemove", onMouseMove);
    document.body.addEventListener("mouseover", handleMouseOver);
    document.body.addEventListener("mouseout", handleMouseOut);

    return () => {
      document.head.removeChild(style);
      document.body.removeEventListener("mousemove", onMouseMove);
      document.body.removeEventListener("mouseover", handleMouseOver);
      document.body.removeEventListener("mouseout", handleMouseOut);
    };
  }, []);

  return (
    <div className="pointer-events-none fixed inset-0 z-[99999] mix-blend-difference overflow-hidden">
      <div 
        ref={bigBallRef} 
        className="absolute top-0 left-0"
        style={{ willChange: "transform" }}
      >
        <svg height="30" width="30">
          <circle cx="15" cy="15" r="12" strokeWidth="0" fill="#f7f8fa"></circle>
        </svg>
      </div>
      
      <div 
        ref={smallBallRef} 
        className="absolute top-0 left-0"
        style={{ willChange: "transform" }}
      >
        <svg height="10" width="10">
          <circle cx="5" cy="5" r="4" strokeWidth="0" fill="#000000"></circle>
        </svg>
      </div>
    </div>
  );
}
