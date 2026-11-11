// TapToPlace.cs -- drop-in plane detection and 1:1 placement for AR Foundation.
//
// Put this on the XR Origin, assign a machine prefab, build to an ARCore
// Android device. Tap a detected plane to stand the machine on it; tap again
// elsewhere to move it; two-finger drag to rotate it on the spot.
//
// Deliberately no scaling gesture: these models are life size, and letting a
// trainee pinch a 220 t truck down to the size of a toy destroys the one thing
// AR adds over a picture on a slide. If you want a tabletop mode, expose it as
// an explicit button with fixed scale steps (1:1, 1:10, 1:25) rather than a
// free pinch, so the scale on screen is always a known number.
//
// Tested against AR Foundation 5.1 / 6.0. On AR Foundation 6 the raycast and
// plane APIs below are unchanged; only the namespace of XROrigin differs by
// Unity version (Unity.XR.CoreUtils in 2021.2+).

using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

[RequireComponent(typeof(ARRaycastManager))]
public class TapToPlace : MonoBehaviour
{
    [Header("What to place")]
    [Tooltip("Machine prefab. Must be authored in metres at 1:1 scale.")]
    public GameObject machinePrefab;

    [Header("Behaviour")]
    [Tooltip("Face the machine towards the camera when it is first placed.")]
    public bool faceCameraOnPlace = true;

    [Tooltip("Degrees of yaw per 100 px of two-finger drag.")]
    public float rotateSensitivity = 45f;

    [Tooltip("Hide detected plane visualisations once the machine is down.")]
    public bool hidePlanesAfterPlacement = true;

    public GameObject Placed { get; private set; }

    ARRaycastManager _raycaster;
    ARPlaneManager _planes;
    Camera _camera;
    readonly List<ARRaycastHit> _hits = new List<ARRaycastHit>();
    float _lastTwoFingerAngle;

    void Awake()
    {
        _raycaster = GetComponent<ARRaycastManager>();
        _planes = GetComponent<ARPlaneManager>();
        _camera = Camera.main;
    }

    void Update()
    {
        if (Input.touchCount == 2)
        {
            RotateWithTwoFingers();
            return;
        }

        if (Input.touchCount != 1) return;
        Touch touch = Input.GetTouch(0);
        if (touch.phase != TouchPhase.Began) return;
        if (IsOverUI(touch.position)) return;

        if (!_raycaster.Raycast(touch.position, _hits, TrackableType.PlaneWithinPolygon))
            return;

        Pose pose = _hits[0].pose;

        if (Placed == null)
        {
            Placed = Instantiate(machinePrefab, pose.position, pose.rotation);
            if (faceCameraOnPlace) FaceCamera(Placed.transform);
            if (hidePlanesAfterPlacement) SetPlanesVisible(false);
        }
        else
        {
            Placed.transform.position = pose.position;
        }
    }

    void FaceCamera(Transform t)
    {
        if (_camera == null) return;
        Vector3 toCamera = _camera.transform.position - t.position;
        toCamera.y = 0f;
        if (toCamera.sqrMagnitude > 0.0001f)
            t.rotation = Quaternion.LookRotation(toCamera, Vector3.up);
    }

    void RotateWithTwoFingers()
    {
        if (Placed == null) return;
        Touch a = Input.GetTouch(0), b = Input.GetTouch(1);
        float angle = Mathf.Atan2(b.position.y - a.position.y,
                                  b.position.x - a.position.x) * Mathf.Rad2Deg;

        if (a.phase == TouchPhase.Began || b.phase == TouchPhase.Began)
        {
            _lastTwoFingerAngle = angle;
            return;
        }

        float delta = Mathf.DeltaAngle(_lastTwoFingerAngle, angle);
        _lastTwoFingerAngle = angle;
        Placed.transform.Rotate(Vector3.up, -delta * rotateSensitivity / 45f, Space.World);
    }

    void SetPlanesVisible(bool visible)
    {
        if (_planes == null) return;
        foreach (ARPlane plane in _planes.trackables)
            plane.gameObject.SetActive(visible);
        _planes.enabled = visible;
    }

    static bool IsOverUI(Vector2 screenPosition)
    {
        var es = UnityEngine.EventSystems.EventSystem.current;
        if (es == null) return false;
        var data = new UnityEngine.EventSystems.PointerEventData(es) { position = screenPosition };
        var results = new List<UnityEngine.EventSystems.RaycastResult>();
        es.RaycastAll(data, results);
        return results.Count > 0;
    }

    /// <summary>Remove the placed machine and bring plane detection back.</summary>
    public void Clear()
    {
        if (Placed != null) Destroy(Placed);
        Placed = null;
        SetPlanesVisible(true);
    }
}
