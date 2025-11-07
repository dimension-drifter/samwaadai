"""
Test to analyze raw audio data from WebSocket
"""
import struct
import wave

def analyze_audio_file(filename):
    """Analyze a WAV file"""
    print(f"\n{'='*60}")
    print(f"Analyzing: {filename}")
    print('='*60)
    
    try:
        with wave.open(filename, 'rb') as wf:
            print(f"\n📊 WAV File Information:")
            print(f"   Channels: {wf.getnchannels()}")
            print(f"   Sample Width: {wf.getsampwidth()} bytes ({wf.getsampwidth()*8}-bit)")
            print(f"   Frame Rate: {wf.getframerate()}Hz")
            print(f"   Frames: {wf.getnframes()}")
            print(f"   Duration: {wf.getnframes()/wf.getframerate():.2f} seconds")
            
            # Read audio data
            audio_data = wf.readframes(wf.getnframes())
            print(f"   Total bytes: {len(audio_data)}")
            
            # Analyze samples
            sample_width = wf.getsampwidth()
            if sample_width == 2:
                samples = struct.unpack(f'{len(audio_data)//2}h', audio_data)
                
                # Calculate statistics
                max_amp = max(abs(s) for s in samples)
                min_val = min(samples)
                max_val = max(samples)
                avg = sum(samples) / len(samples)
                rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
                
                print(f"\n🔊 Audio Signal Analysis:")
                print(f"   Max Amplitude: {max_amp} (out of 32768)")
                print(f"   Min Value: {min_val}")
                print(f"   Max Value: {max_val}")
                print(f"   Average: {avg:.2f}")
                print(f"   RMS Level: {rms:.2f}")
                
                # Check for silence
                if max_amp < 100:
                    print(f"\n⚠️  WARNING: Audio is EXTREMELY quiet (max: {max_amp})")
                    print(f"   This indicates:")
                    print(f"   1. Microphone is muted or not working")
                    print(f"   2. Audio data is corrupted")
                    print(f"   3. Wrong audio format/encoding")
                elif max_amp < 1000:
                    print(f"\n⚠️  Audio is very quiet (max: {max_amp})")
                else:
                    print(f"\n✅ Audio level looks good!")
                
                # Sample first 10 values
                print(f"\n📝 First 10 samples: {samples[:10]}")
                
                # Check for clipping
                clipped = sum(1 for s in samples if abs(s) >= 32767)
                if clipped > 0:
                    print(f"\n⚠️  {clipped} samples are clipped ({clipped/len(samples)*100:.2f}%)")
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    import os
    
    # Find debug files
    debug_files = [f for f in os.listdir('.') if f.startswith('debug_recording_')]
    
    if not debug_files:
        print("❌ No debug recording files found!")
        print("   Record something in the app first.")
        sys.exit(1)
    
    # Analyze latest debug file
    latest = sorted(debug_files)[-1]
    analyze_audio_file(latest)