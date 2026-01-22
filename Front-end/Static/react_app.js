const { useState, useEffect, useRef } = React;

const ThreeScene = ({ status }) => {
    const mountRef = useRef(null);

    useEffect(() => {
        // --- THREE.JS SETUP ---
        const width = mountRef.current.clientWidth;
        const height = mountRef.current.clientHeight;

        const scene = new THREE.Scene();
        // Fog for depth
        scene.fog = new THREE.FogExp2(0x000000, 0.002);

        const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
        camera.position.z = 20;

        const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(window.devicePixelRatio);
        mountRef.current.appendChild(renderer.domElement);

        // --- MESH CREATION (PARTICLE SPHERE) ---
        const geometry = new THREE.IcosahedronGeometry(10, 4);
        const count = geometry.attributes.position.count;

        // Add random offsets for animation
        const randoms = new Float32Array(count);
        for (let i = 0; i < count; i++) {
            randoms[i] = Math.random();
        }
        geometry.setAttribute('random', new THREE.BufferAttribute(randoms, 1));

        // Custom Shader Material for glow and movement
        const material = new THREE.ShaderMaterial({
            uniforms: {
                time: { value: 0 },
                color: { value: new THREE.Color(0x44aaff) },
                activity: { value: 0.0 }
            },
            vertexShader: `
                uniform float time;
                uniform float activity;
                attribute float random;
                varying vec3 vNormal;
                
                void main() {
                    vNormal = normal;
                    
                    // Pulse effect based on activity (status)
                    float pulse = sin(time * 3.0 + random * 10.0) * activity * 1.5;
                    
                    // Basic wave distortion
                    vec3 newPos = position + normal * pulse;
                    
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(newPos, 1.0);
                    gl_PointSize = 4.0;
                }
            `,
            fragmentShader: `
                uniform vec3 color;
                void main() {
                    // Circular particles
                    if (length(gl_PointCoord - vec2(0.5)) > 0.5) discard;
                    gl_FragColor = vec4(color, 0.8);
                }
            `,
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        const particles = new THREE.Points(geometry, material);
        scene.add(particles);

        // Ambient glow
        const glowGeo = new THREE.SphereGeometry(9, 32, 32);
        const glowMat = new THREE.MeshBasicMaterial({ color: 0x001133, transparent: true, opacity: 0.1 });
        const glowSphere = new THREE.Mesh(glowGeo, glowMat);
        scene.add(glowSphere);

        // --- ANIMATION ---
        let frameId;
        const animate = () => {
            frameId = requestAnimationFrame(animate);

            material.uniforms.time.value += 0.01;

            // Rotate sphere
            particles.rotation.y += 0.002;
            particles.rotation.x += 0.001;

            // React to Status
            let targetActivity = 0.0;
            let targetColor = new THREE.Color(0x44aaff); // Idle Blue

            if (status === 'listening') {
                targetActivity = 1.0; // High Pulse
                targetColor.setHex(0x00ff88); // Green
                particles.rotation.y += 0.02; // Fast spin
            } else if (status === 'processing') {
                targetActivity = 0.5;
                targetColor.setHex(0xaaddff); // White-ish
                particles.rotation.y += 0.05; // Very fast spin
            } else if (status === 'speaking') {
                targetActivity = 0.8;
                targetColor.setHex(0xaa00ff); // Purple
                // Pulse with time
                material.uniforms.activity.value = (Math.sin(Date.now() * 0.01) + 1) * 0.5;
            }

            // Smoothly interpolate current values to target
            material.uniforms.activity.value = THREE.MathUtils.lerp(material.uniforms.activity.value, targetActivity, 0.1);
            material.uniforms.color.value.lerp(targetColor, 0.05);

            renderer.render(scene, camera);
        };
        animate();

        // Handle Resize
        const handleResize = () => {
            if (!mountRef.current) return;
            width = mountRef.current.clientWidth;
            height = mountRef.current.clientHeight;
            renderer.setSize(width, height);
            camera.aspect = width / height;
            camera.updateProjectionMatrix();
        };
        // window.addEventListener('resize', handleResize);

        return () => {
            cancelAnimationFrame(frameId);
            // window.removeEventListener('resize', handleResize);
            if (mountRef.current && renderer.domElement) {
                mountRef.current.removeChild(renderer.domElement);
            }
            geometry.dispose();
            material.dispose();
        };
    }, [status]);

    return <div ref={mountRef} className="three-container" />;
};

const App = () => {
    const [status, setStatus] = useState("idle");
    const [lastInput, setLastInput] = useState("");
    const [lastResponse, setLastResponse] = useState("I am ready.");
    const [inputValue, setInputValue] = useState("");
    const [showFullLog, setShowFullLog] = useState(false);
    const recognitionRef = useRef(null);

    const speakResponse = (text) => {
        if (!window.speechSynthesis) return;
        setStatus("speaking");
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.onend = () => setStatus("idle");
        window.speechSynthesis.speak(utterance);
    };

    const processCommand = async (command) => {
        if (!command.trim()) return;

        setStatus("processing");
        setLastInput(command);

        try {
            const res = await fetch('/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command })
            });
            const data = await res.json();

            setLastResponse(data.response);
            speakResponse(data.response);
        } catch (error) {
            setLastResponse("Error connecting to server.");
            setStatus("idle");
        }
    };

    const startListening = () => {
        if (status === "listening") {
            recognitionRef.current?.stop();
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            setLastResponse("Speech recognition not supported.");
            return;
        }

        const recognition = new SpeechRecognition();
        recognitionRef.current = recognition;
        recognition.continuous = false;
        recognition.lang = 'en-US';
        recognition.interimResults = false;

        recognition.onstart = () => {
            setStatus("listening");
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            processCommand(transcript);
        };

        recognition.onerror = (event) => {
            setStatus("idle");
            setLastResponse(`Error: ${event.error}`);
        };

        recognition.onend = () => {
            if (status === "listening") setStatus("idle");
        };

        recognition.start();
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            processCommand(inputValue);
            setInputValue("");
        }
    };

    return (
        <div className="main-wrapper">
            {/* 3D Background Layer */}
            <ThreeScene status={status} />

            {/* Foreground UI Layer */}
            <div className="ui-layer">

                <header>
                    <h3>ALEXA AI</h3>
                </header>

                <div className="center-info">
                    {status === 'listening' && <div className="listening-indicator">Listening...</div>}
                    <div className="conversation-display">
                        {lastInput && <p className="user-text">"{lastInput}"</p>}
                        <p className="ai-text">{lastResponse}</p>
                    </div>
                </div>

                <div className="control-bar">
                    <button className={`mic-btn ${status}`} onClick={startListening}>
                        {status === 'listening' ? 'STOP' : 'MIC'}
                    </button>
                    <input
                        type="text"
                        value={inputValue}
                        onChange={e => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Type a command..."
                    />
                </div>

            </div>
        </div>
    );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
