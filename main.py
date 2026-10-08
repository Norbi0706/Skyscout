"""
Skyscout: Flight Search API powered by FastAPI and Amadeus
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from amadeus import Client, ResponseError

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Skyscout",
    description="Flight search and booking API",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Amadeus client
try:
    amadeus = Client(
        client_id=os.getenv("AMADEUS_CLIENT_ID"),
        client_secret=os.getenv("AMADEUS_CLIENT_SECRET")
    )
except Exception as e:
    print(f"Warning: Amadeus client initialization failed: {e}")
    amadeus = None


# Pydantic models
class FlightSearchRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str
    return_date: str = None
    adults: int = 1
    children: int = 0
    infants: int = 0


class FlightOffer(BaseModel):
    id: str
    source: str
    instantTicketingRequired: bool
    nonHomogeneous: bool
    oneWay: bool
    lastTicketingDate: str
    numberOfBookableSeats: int
    itineraries: list
    price: dict
    pricingOptions: dict
    validatingAirlineCodes: list
    travelerPricings: list


class FlightSearchResponse(BaseModel):
    success: bool
    data: list = []
    message: str = ""


# Routes
@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "name": "Skyscout",
        "version": "0.1.0",
        "description": "Flight search API powered by Amadeus",
        "endpoints": {
            "health": "/health",
            "search_flights": "/flights/search"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    amadeus_status = "connected" if amadeus else "not_configured"
    return {
        "status": "ok",
        "amadeus": amadeus_status
    }


@app.post("/flights/search", response_model=FlightSearchResponse)
async def search_flights(request: FlightSearchRequest):
    """
    Search for flights using Amadeus Flight Search API
    
    Args:
        origin: IATA code (e.g., 'NYC')
        destination: IATA code (e.g., 'LAX')
        departure_date: Date in YYYY-MM-DD format
        return_date: Optional return date in YYYY-MM-DD format
        adults: Number of adult passengers
        children: Number of child passengers
        infants: Number of infant passengers
    
    Returns:
        List of flight offers with pricing and itinerary details
    """
    
    if not amadeus:
        raise HTTPException(
            status_code=503,
            detail="Amadeus client not configured. Please set AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET in .env"
        )
    
    try:
        # Build search parameters
        params = {
            "originLocationCode": request.origin,
            "destinationLocationCode": request.destination,
            "departureDate": request.departure_date,
            "adults": str(request.adults),
        }
        
        if request.children > 0:
            params["children"] = str(request.children)
        
        if request.infants > 0:
            params["infants"] = str(request.infants)
        
        if request.return_date:
            params["returnDate"] = request.return_date
        
        # Call Amadeus Flight Search API
        response = amadeus.shopping.flight_offers_search.get(**params)
        
        return FlightSearchResponse(
            success=True,
            data=response.data if response.data else [],
            message=f"Found {len(response.data) if response.data else 0} flight offers"
        )
    
    except ResponseError as error:
        raise HTTPException(
            status_code=400,
            detail=f"Amadeus API error: {error.response['errors'][0]['detail'] if error.response.get('errors') else 'Unknown error'}"
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching flights: {str(error)}"
        )


@app.get("/flights/inspire")
async def flight_inspiration(
    origin: str = Query(..., description="IATA code (e.g., 'NYC')"),
    max_price: int = Query(None, description="Maximum price in USD")
):
    """
    Get flight inspiration (cheapest destinations from origin)
    
    Args:
        origin: IATA code
        max_price: Optional maximum price filter
    
    Returns:
        List of inspiration destinations with prices
    """
    
    if not amadeus:
        raise HTTPException(
            status_code=503,
            detail="Amadeus client not configured"
        )
    
    try:
        params = {"origin": origin}
        if max_price:
            params["maxPrice"] = str(max_price)
        
        response = amadeus.reference_data.recommended_locations.get(**params)
        
        return {
            "success": True,
            "origin": origin,
            "destinations": response.data if response.data else [],
            "count": len(response.data) if response.data else 0
        }
    
    except ResponseError as error:
        raise HTTPException(
            status_code=400,
            detail=f"Amadeus API error: {error.response['errors'][0]['detail'] if error.response.get('errors') else 'Unknown error'}"
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching inspiration: {str(error)}"
        )


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port)
