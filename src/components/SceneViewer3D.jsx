import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

export default function SceneViewer3D({ worldModel, selectedObjectId, onSelectObject }) {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const cameraRef = useRef(null);
  const objectsGroupRef = useRef(null);
  const lidarPointsRef = useRef(null);

  useEffect(() => {
    if (!mountRef.current) return;

    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight;

    // 1. Three.js Scene Setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x090d16);
    scene.fog = new THREE.FogExp2(0x090d16, 0.015);
    sceneRef.current = scene;

    // 2. Camera Setup
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 500);
    camera.position.set(0, -35, 25);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // 3. Renderer Setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    mountRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. Lighting & Environment
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x60a5fa, 1.2);
    dirLight.position.set(20, -30, 50);
    scene.add(dirLight);

    // 5. Grid Helper & Ground Plane
    const gridHelper = new THREE.GridHelper(120, 60, 0x3b82f6, 0x1e293b);
    gridHelper.rotation.x = Math.PI / 2;
    scene.add(gridHelper);

    // 6. Ego Vehicle Model (Center)
    const egoGroup = new THREE.Group();
    const egoGeo = new THREE.BoxGeometry(2.0, 4.5, 1.5);
    const egoMat = new THREE.MeshStandardMaterial({ color: 0x3b82f6, transparent: true, opacity: 0.8, roughness: 0.2 });
    const egoMesh = new THREE.Mesh(egoGeo, egoMat);
    egoMesh.position.z = 0.75;
    egoGroup.add(egoMesh);

    // Ego heading arrow
    const arrowDir = new THREE.Vector3(0, 1, 0);
    const arrowHelper = new THREE.ArrowHelper(arrowDir, new THREE.Vector3(0, 0, 1.5), 4, 0x60a5fa, 1, 0.5);
    egoGroup.add(arrowHelper);
    scene.add(egoGroup);

    // Groups for dynamic elements
    const objectsGroup = new THREE.Group();
    scene.add(objectsGroup);
    objectsGroupRef.current = objectsGroup;

    // 7. Mouse Orbit Controls (Basic drag-to-rotate)
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };

    const handleMouseDown = (e) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e) => {
      if (!isDragging || !cameraRef.current) return;

      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;

      const radius = cameraRef.current.position.length();
      let theta = Math.atan2(cameraRef.current.position.x, cameraRef.current.position.y);
      let phi = Math.acos(cameraRef.current.position.z / radius);

      theta -= deltaX * 0.008;
      phi = Math.max(0.1, Math.min(Math.PI / 2 - 0.05, phi - deltaY * 0.008));

      cameraRef.current.position.x = radius * Math.sin(phi) * Math.sin(theta);
      cameraRef.current.position.y = radius * Math.sin(phi) * Math.cos(theta);
      cameraRef.current.position.z = radius * Math.cos(phi);
      cameraRef.current.lookAt(0, 0, 0);

      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const handleMouseUp = () => { isDragging = false; };

    const handleWheel = (e) => {
      if (!cameraRef.current) return;
      const factor = e.deltaY > 0 ? 1.08 : 0.92;
      cameraRef.current.position.multiplyScalar(factor);
      cameraRef.current.lookAt(0, 0, 0);
    };

    const domElem = mountRef.current;
    domElem.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    domElem.addEventListener('wheel', handleWheel);

    // 8. Animation Loop
    let animId;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
      }
    };
    animate();

    const handleResize = () => {
      if (!mountRef.current || !rendererRef.current || !cameraRef.current) return;
      const newW = mountRef.current.clientWidth;
      const newH = mountRef.current.clientHeight;
      cameraRef.current.aspect = newW / newH;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(newW, newH);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      domElem.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      domElem.removeEventListener('wheel', handleWheel);
      window.removeEventListener('resize', handleResize);
      if (rendererRef.current && rendererRef.current.domElement) {
        rendererRef.current.domElement.remove();
      }
    };
  }, []);

  // Update 3D Scene whenever WorldModel changes
  useEffect(() => {
    if (!objectsGroupRef.current || !worldModel) return;

    // Clear existing dynamic objects
    while (objectsGroupRef.current.children.length > 0) {
      const child = objectsGroupRef.current.children[0];
      objectsGroupRef.current.remove(child);
    }

    const objects = worldModel.objects || {};

    Object.values(objects).forEach((obj) => {
      const isSelected = obj.id === selectedObjectId;
      const isCritical = obj.risk_score > 0.8;
      const isHigh = obj.risk_score > 0.4;

      // Color coding: Critical (Red), High Risk (Orange/Yellow), Vehicle (Blue/Cyan), Pedestrian (Green)
      let boxColor = 0x38bdf8;
      if (obj.category.includes('pedestrian')) boxColor = 0x34d399;
      if (isHigh) boxColor = 0xfbbf24;
      if (isCritical) boxColor = 0xf87171;
      if (isSelected) boxColor = 0xa855f7;

      const size = obj.size || [2, 4, 1.5];
      const pos = obj.position || [0, 0, 0];

      const boxGeo = new THREE.BoxGeometry(size[0], size[1], size[2]);
      const boxMat = new THREE.MeshStandardMaterial({
        color: boxColor,
        transparent: true,
        opacity: isSelected ? 0.9 : 0.6,
        wireframe: false
      });
      const mesh = new THREE.Mesh(boxGeo, boxMat);
      mesh.position.set(pos[0], pos[1], pos[2]);
      mesh.userData = { id: obj.id, data: obj };

      // Wireframe overlay border
      const edges = new THREE.EdgesGeometry(boxGeo);
      const lineMat = new THREE.LineBasicMaterial({ color: isSelected ? 0xd8b4fe : boxColor, linewidth: 2 });
      const wireframe = new THREE.LineSegments(edges, lineMat);
      mesh.add(wireframe);

      // Trajectory forecast line (PyTorch LSTM predictions)
      if (obj.predicted_trajectory && obj.predicted_trajectory.length > 0) {
        const points = [];
        points.push(new THREE.Vector3(pos[0], pos[1], pos[2]));
        obj.predicted_trajectory.forEach((pt) => {
          points.push(new THREE.Vector3(pt[0], pt[1], pos[2]));
        });

        const trajGeo = new THREE.BufferGeometry().setFromPoints(points);
        const trajMat = new THREE.LineDashedMaterial({
          color: isCritical ? 0xef4444 : 0x60a5fa,
          dashSize: 0.8,
          gapSize: 0.4,
          linewidth: 3
        });
        const trajLine = new THREE.Line(trajGeo, trajMat);
        trajLine.computeLineDistances();
        objectsGroupRef.current.add(trajLine);
      }

      objectsGroupRef.current.add(mesh);
    });

  }, [worldModel, selectedObjectId]);

  return (
    <div className="relative w-full h-full select-none" mountref={mountRef}>
      <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />
      
      {/* 3D Viewport Controls HUD Overlay */}
      <div className="absolute top-4 left-4 glass-panel px-3 py-2 rounded-lg text-xs font-mono text-slate-300 flex items-center gap-3">
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span> Ego Vehicle</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-cyan-400"></span> Detected 3D Object</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400"></span> Pedestrian</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red-400"></span> High Collision Risk</span>
      </div>

      <div className="absolute bottom-4 left-4 glass-panel px-3 py-1.5 rounded text-xs text-slate-400">
        🖱️ Drag: Rotate Camera | Scroll: Zoom | Click Object: Select & Inspect
      </div>
    </div>
  );
}
