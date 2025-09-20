import requests
import json
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_root_endpoint():
    """Test the root endpoint"""
    print("\nTesting root endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Root endpoint test failed: {e}")
        return False

def test_generate_map(bbox_data: Dict[str, float], test_name: str, save_filename: str = None):
    """Test the map generation endpoint"""
    print(f"\n{test_name}...")
    print(f"Bounding box: {bbox_data}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/generate-map",
            json=bbox_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            # Save the image
            filename = save_filename or f"test_map_{test_name.lower().replace(' ', '_')}.png"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✅ Map generated successfully! Saved as: {filename}")
            print(f"Image size: {len(response.content)} bytes")
            return True
        else:
            print(f"❌ Failed to generate map")
            try:
                error_detail = response.json()
                print(f"Error: {error_detail}")
            except:
                print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

def test_invalid_coordinates():
    """Test with invalid coordinate bounds"""
    print("\nTesting invalid coordinates (should fail)...")
    
    invalid_cases = [
        {
            "name": "South >= North",
            "data": {"south": 40.5, "west": -74.7, "north": 40.3, "east": -74.6}
        },
        {
            "name": "West >= East", 
            "data": {"south": 40.3, "west": -74.6, "north": 40.5, "east": -74.7}
        },
        {
            "name": "Invalid latitude range",
            "data": {"south": -95.0, "west": -74.7, "north": 40.5, "east": -74.6}
        }
    ]
    
    for case in invalid_cases:
        print(f"\n  Testing {case['name']}...")
        try:
            response = requests.post(
                f"{BASE_URL}/generate-map",
                json=case["data"],
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [400, 422]:  # Both are valid error codes
                try:
                    error_detail = response.json()
                    if 'detail' in error_detail:
                        detail = error_detail['detail']
                        if isinstance(detail, list) and len(detail) > 0:
                            detail = detail[0].get('msg', str(detail))
                        print(f"  ✅ Correctly rejected invalid input: {detail}")
                    else:
                        print(f"  ✅ Correctly rejected invalid input with status {response.status_code}")
                except:
                    print(f"  ✅ Correctly rejected invalid input with status {response.status_code}")
            else:
                print(f"  ❌ Should have rejected invalid input but got status: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Error testing invalid case: {e}")

def run_all_tests():
    """Run all API tests"""
    print("🚀 Starting API Tests")
    print("=" * 50)
    
    # Test basic endpoints
    health_ok = test_health_check()
    root_ok = test_root_endpoint()
    
    if not health_ok:
        print("\n❌ Health check failed - is the server running?")
        return
    
    # Test map generation with different locations
    test_cases = [
        {
            "name": "Princeton, NJ (Original)",
            "bbox": {"south": 40.30, "west": -74.70, "north": 40.38, "east": -74.60},
            "filename": "princeton_nj_map.png"
        },
        {
            "name": "Small area test",
            "bbox": {"south": 40.32, "west": -74.68, "north": 40.34, "east": -74.66},
            "filename": "small_area_test.png"
        },
        {
            "name": "NYC Central Park area",
            "bbox": {"south": 40.76, "west": -73.98, "north": 40.80, "east": -73.94},
            "filename": "central_park_nyc.png"
        }
    ]
    
    success_count = 0
    for test_case in test_cases:
        if test_generate_map(test_case["bbox"], test_case["name"], test_case["filename"]):
            success_count += 1
    
    # Test error handling
    test_invalid_coordinates()
    
    print("\n" + "=" * 50)
    print(f"🏁 Tests completed: {success_count}/{len(test_cases)} map generation tests passed")
    
    if success_count == len(test_cases):
        print("✅ All tests passed! Your API is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    # Instructions
    print("FastAPI Map Generator Test Client")
    print("=" * 50)
    print("Before running tests, make sure to:")
    print("1. Install required packages: pip install fastapi uvicorn requests")
    print("2. Start the API server: python map_api.py")
    print("3. Then run this test script in another terminal")
    print()
    
    # Run tests
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
    except Exception as e:
        print(f"\n\nUnexpected error during testing: {e}")