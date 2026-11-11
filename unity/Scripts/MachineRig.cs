// MachineRig.cs -- drives the articulated parts of a generated machine.
//
// The GLB files from tools/make_*.py are not a single welded mesh: each part
// is its own named node, and the moving ones are parented into a real
// kinematic chain with their geometry expressed about the joint they hinge on.
//
//   shovel : superstructure -> boom -> stick -> bucket -> bucket_teeth
//   dumper : dump_body -> body_canopy
//
// So you can rotate "boom" and the stick, bucket and teeth follow, exactly as
// they do on the machine. This component finds those transforms by name and
// gives you angles in degrees, plus a demo cycle for a lesson.
//
// AXIS CONVENTION: the models are authored with every linkage lying in a
// vertical fore-aft plane, so booms, sticks, buckets and dump bodies all hinge
// about their local X axis, and the shovel's upper works slews about Y.
// glTF is right-handed and Unity is left-handed, so an importer (glTFast,
// or an FBX round trip through Blender) flips one axis -- which can flip the
// sign of a rotation. If a lever swings the wrong way, set the matching
// invert flag below rather than editing the model.

using System.Collections;
using UnityEngine;

public class MachineRig : MonoBehaviour
{
    [Header("Part names as exported (leave blank if absent)")]
    public string swingNode = "superstructure";
    public string boomNode = "boom";
    public string stickNode = "stick";
    public string bucketNode = "bucket";
    public string dumpBodyNode = "dump_body";

    [Header("Axis direction")]
    public bool invertHingeAxis = false;
    public bool invertSwingAxis = false;

    [Header("Limits (degrees)")]
    public Vector2 boomRange = new Vector2(-25f, 30f);
    public Vector2 stickRange = new Vector2(-35f, 35f);
    public Vector2 bucketRange = new Vector2(-40f, 25f);
    public Vector2 dumpBodyRange = new Vector2(0f, 45f);

    Transform _swing, _boom, _stick, _bucket, _body;
    Quaternion _swing0, _boom0, _stick0, _bucket0, _body0;

    void Awake()
    {
        _swing = Find(swingNode);
        _boom = Find(boomNode);
        _stick = Find(stickNode);
        _bucket = Find(bucketNode);
        _body = Find(dumpBodyNode);

        if (_swing) _swing0 = _swing.localRotation;
        if (_boom) _boom0 = _boom.localRotation;
        if (_stick) _stick0 = _stick.localRotation;
        if (_bucket) _bucket0 = _bucket.localRotation;
        if (_body) _body0 = _body.localRotation;
    }

    Transform Find(string nodeName)
    {
        if (string.IsNullOrEmpty(nodeName)) return null;
        foreach (Transform t in GetComponentsInChildren<Transform>(true))
            if (t.name == nodeName) return t;
        Debug.LogWarning($"MachineRig: no child named '{nodeName}' under {name}", this);
        return null;
    }

    float Hinge(float degrees) => invertHingeAxis ? -degrees : degrees;
    float Swing(float degrees) => invertSwingAxis ? -degrees : degrees;

    // ---- direct control, 0 = the exported rest pose -----------------------

    public void SetSwing(float degrees)
    {
        if (_swing) _swing.localRotation = _swing0 * Quaternion.Euler(0f, Swing(degrees), 0f);
    }

    public void SetBoom(float degrees)
    {
        degrees = Mathf.Clamp(degrees, boomRange.x, boomRange.y);
        if (_boom) _boom.localRotation = _boom0 * Quaternion.Euler(Hinge(degrees), 0f, 0f);
    }

    public void SetStick(float degrees)
    {
        degrees = Mathf.Clamp(degrees, stickRange.x, stickRange.y);
        if (_stick) _stick.localRotation = _stick0 * Quaternion.Euler(Hinge(degrees), 0f, 0f);
    }

    public void SetBucket(float degrees)
    {
        degrees = Mathf.Clamp(degrees, bucketRange.x, bucketRange.y);
        if (_bucket) _bucket.localRotation = _bucket0 * Quaternion.Euler(Hinge(degrees), 0f, 0f);
    }

    public void SetDumpBody(float degrees)
    {
        degrees = Mathf.Clamp(degrees, dumpBodyRange.x, dumpBodyRange.y);
        if (_body) _body.localRotation = _body0 * Quaternion.Euler(Hinge(-degrees), 0f, 0f);
    }

    public void ResetPose()
    {
        SetSwing(0f); SetBoom(0f); SetStick(0f); SetBucket(0f); SetDumpBody(0f);
    }

    // ---- demo cycles ------------------------------------------------------

    /// <summary>One shovel cycle: dig, swing to the truck, dump, swing back.
    /// Timings match a real 140 t machine, roughly 30 s door to door, which is
    /// the number worth showing a class -- productivity is cycles per hour.</summary>
    public IEnumerator ShovelCycle(float swingDegrees = 90f)
    {
        yield return Sweep(SetBucket, 0f, -30f, 2.0f);     // crowd into the face
        yield return Sweep(SetBoom, 0f, 14f, 3.5f);        // lift the loaded bucket
        yield return Sweep(SetSwing, 0f, swingDegrees, 6.0f);
        yield return Sweep(SetBucket, -30f, 20f, 2.5f);    // dump into the truck
        yield return new WaitForSeconds(0.6f);
        yield return Sweep(SetSwing, swingDegrees, 0f, 6.0f);
        yield return Sweep(SetBoom, 14f, 0f, 3.0f);
        yield return Sweep(SetBucket, 20f, 0f, 1.5f);
    }

    /// <summary>One dumper tip: raise the body, hold, lower.</summary>
    public IEnumerator DumpCycle()
    {
        yield return Sweep(SetDumpBody, 0f, 45f, 13f);
        yield return new WaitForSeconds(2f);
        yield return Sweep(SetDumpBody, 45f, 0f, 11f);
    }

    IEnumerator Sweep(System.Action<float> set, float from, float to, float seconds)
    {
        float t = 0f;
        while (t < seconds)
        {
            t += Time.deltaTime;
            float k = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(t / seconds));
            set(Mathf.Lerp(from, to, k));
            yield return null;
        }
        set(to);
    }
}
