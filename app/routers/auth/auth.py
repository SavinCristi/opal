import json
import logging
import os
from typing import Any, Dict, List, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder 
from sqlalchemy.future import select
from app.database.database import get_db_session
from app.permit.permit_api import permit
from app.database.models import Organisation, User
from app.permit.permit_api import permit as permit_sdk_client, sync_user 
from permit.api.models import UserCreate 

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/opal", # All routes here will be under /opal
    tags=["OPAL & Permit.io Debugging"]
)

PERMIT_API_BASE_URL =  os.getenv(
    "permit_url",
    "https://api.permit.io/v2"
)  
LOCAL_PDP_OPA_URL  = os.getenv(
    "local_opa_url",
    "http://permit_pdp:8181" 
)  
PERMIT_MANAGEMENT_API_KEY = os.getenv(
    "permit_api_key",
    "permit_key_DYCCSN4SZMeKyC37I879gJABnmSlpnvqavBbCMJGr50JoekDgECAQ6c7nKyZMmYwMpSgEAz51cJtfW7PaWtPbr"
)  

ENV_ID = os.getenv(
    "env_id",
    "9177328c79be438d9d3cfab3ec759fbc"
) 
ORG_ID = os.getenv(
    "org_id",
    "f994c767471444dd8efb7a4a78043775"
) 

PDP_ID = os.getenv(
    "pdp_id",
    "5f41482c344c4a1882af39ea1a0e44a3"
) 

PROJECT_ID = os.getenv(
    "project_id",
    "2a4cdf901c5f48b6bd3f80f9579e92a9"
) 


async def get_http_client():
    async with httpx.AsyncClient(timeout=10.0) as client: # Default timeout
        yield client

# --- Helper for Permit.io Cloud API calls ---
async def make_permit_cloud_request(
    client: httpx.AsyncClient, 
    method: str, 
    endpoint: str, 
    payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    url = f"{PERMIT_API_BASE_URL}{endpoint}" 
    headers = {
        "Authorization": f"Bearer {PERMIT_MANAGEMENT_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    logger.info(f"Requesting Permit.io Cloud: {method.upper()} {url}")
    if payload:
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = await client.request(method, url, headers=headers, json=payload if payload else None)
        logger.info(f"Permit.io Cloud Response: {response.status_code}")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Permit.io Cloud API HTTPStatusError: {e.response.status_code} - Body: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Permit.io API Error: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Permit.io Cloud API RequestError: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Network error connecting to Permit.io API: {str(e)}")

# --- Helper for Local OPA API calls ---
async def make_local_opa_request(
    client: httpx.AsyncClient,
    method: str,
    endpoint: str, 
    content: Optional[str] = None,
    json_payload: Optional[Dict[str, Any]] = None 
) -> Dict[str, Any]:
    url = f"{LOCAL_PDP_OPA_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {PERMIT_MANAGEMENT_API_KEY}"}
    if content: 
        headers["Content-Type"] = "text/plain"
    elif json_payload: 
        headers["Content-Type"] = "application/json"
    
    logger.info(f"Requesting Local OPA: {method.upper()} {url}")
    if content: logger.debug(f"Raw Content Length: {len(content)}")
    if json_payload: logger.debug(f"JSON Payload: {json.dumps(json_payload, indent=2)}")

    try:
        response = await client.request(method, url, headers=headers, content=content, json=json_payload)
        logger.info(f"Local OPA Response: {response.status_code}")
        response_text = response.text 
        
        if response.status_code == 204 and method.upper() == "DELETE":
            return {"status": "success", "message": "Delete successful (204 No Content)"}

        response.raise_for_status()
        
        try:
            return response.json()
        except json.JSONDecodeError:
            logger.warning(f"Local OPA Response (Non-JSON or empty): {response_text}")
            return {"status_code": response.status_code, "raw_body": response_text}
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Local OPA API HTTPStatusError: {e.response.status_code} - Body: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Local OPA API Error: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Local OPA API RequestError: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Network error connecting to Local OPA: {str(e)}")



@router.get("/read_current_db_attributes", response_model=List[Dict[str, Any]])
async def read_db_attributes_for_opal(db_session=Depends(get_db_session)):

    logger.info("Fetching users from local DB for OPAL attributes source.")
    try:
        result = await db_session.execute(select(User))
        users = result.scalars().all()
        
        data = [
            {
                "key": user.email,
                "country": getattr(user, 'country', None),
                "position": getattr(user, 'position', None),
                "authority": getattr(user, 'authority', None),
                #"ssm_functions": list(getattr(user, 'SSM_functions', [])) if getattr(user, 'SSM_functions', []) is not None else [],
                "ssm_member": getattr(user, 'isSSM', None),
                "org_unit_level_a": getattr(user, 'org_unit_level_a', None),
                "team": getattr(user, 'team', None),
            }
            for user in users
        ]
        logger.info(f"Successfully fetched and processed {len(data)} users from local DB.")
        return data
    except Exception as e:
        logger.exception("Error fetching users from local DB for OPAL:")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch attributes from database.")


@router.get("/read_organization", response_model=List[Dict[str, Any]])
async def read_db_attributes_for_opal(db_session=Depends(get_db_session)):

    logger.info("Fetching organization attributes from local DB for OPAL attributes source.")
    try:
        result = await db_session.execute(select(Organisation))
        orgs = result.scalars().all()
        
        data = [
            {
                "country": getattr(org, 'country', None),
                "orgpath": getattr(org, 'orgpath', None),
                "name": getattr(org, 'name', None),
                "authority": getattr(org, 'authority', None),
                "approvers": getattr(org, 'approvers', None)
            }
            for org in orgs
        ]
        logger.info(f"Successfully fetched and processed {len(data)} org from local DB.")
        return data
    except Exception as e:
        logger.exception("Error fetching org from local DB for OPAL:")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch attributes from database.")
    
    
@router.get("/check_user_permission")
async def check_user_permission_route(
    email: str = Query(..., description="User's email")
):
    # logger.info(f"Checking permission for user: {email}, action: read, resource: HRS")
    # user_data_to_sync = UserCreate(
    #     key=email,
    #     email=email,
    #     attributes={} # Syncing minimal identity
    # )
    # try:
    #     synced_user_response = await sync_user(user_data_to_sync) 
    #     logger.info(f"User sync response from Permit.io Cloud for {email}: {synced_user_response}")
    # except Exception as e_sync:
    #     logger.error(f"Failed to sync user {email} to Permit.io Cloud during permission check: {e_sync}")

    try:        
        decision = await permit.check(email, 'read', 'HRS', context={"__debug": True})
        #decision = await permit.check(email, 'update', 'newmission:mission_a', context={"__debug": True})
        #return {"email": email, "action": "update", "resource": "newmission:mission_a", "allowed": decision}
        logger.info(f"Permit.check decision for {email}: {decision}")
        return {"email": email, "action": "read", "resource": "HRS", "allowed": decision}
    except Exception as e_check:
        logger.exception(f"Error during permit.check for {email}:")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Permission check failed: {str(e_check)}")
    
    
@router.get("/check_resource_user_country")
async def check_resource_user_country(
    email: str = Query(..., description="User's email"),
    resourceX: str = Query(..., description="Resource's name")
):
    # logger.info(f"Checking permission for user: {email}, action: read, resource: HRS")
    user_data_to_sync = UserCreate(
        key=email,
        email=email,
        attributes={} # Syncing minimal identity
    )
    try:
        synced_user_response = await sync_user(user_data_to_sync) 
        logger.info(f"User sync response from Permit.io Cloud for {email}: {synced_user_response}")
    except Exception as e_sync:
        logger.error(f"Failed to sync user {email} to Permit.io Cloud during permission check: {e_sync}")

    try:        
        decision = await permit.check(email, 'read', resourceX, context={"role": "admin", "__debug": True})
        logger.info(f"Permit.check decision for {email}: {decision}")
        return {"email": email, "action": "read", "resource": resourceX, "allowed": decision}
    except Exception as e_check:
        logger.exception(f"Error during permit.check for {email}:")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Permission check failed: {str(e_check)}")



@router.get("/check_permission_with_inline_attributes")
async def check_permission_with_inline_attributes_route(
    email: str = Query(..., description="User's email"),
):
    logger.info(f"Checking permission for user: {email} with INLINE ATTRIBUTES, action: read, resource: HRS")
    user_data_to_sync = UserCreate(
        key=email,
        email=email,
        attributes={} 
    )
    # try:
        
    #     synced_user_cloud_response = await sync_user(user_data_to_sync) 
    #     logger.info(f"User sync response from Permit.io Cloud for {email}: {synced_user_cloud_response}")
    # except Exception as e_sync:
    #     logger.error(f"Failed to sync user {email} to Permit.io Cloud: {e_sync}. Proceeding with check...")

    # user_object_for_check = {
    #     "key": email,
    #     "attributes": {
    #         "country": "England",       
    #         "debug": "debug_yes" 
    #     }
    # }
    
    logger.info(f"Calling permit.check for user '{email}' with inline attributes: {{'country': 'England', 'debug': 'debug_yes'}}")
    try:
        # decision = await permit.check( 
        #     user=user_object_for_check, 
        #     action='read',
        #     resource_type='HRS' 
        # )
           
        allowed = await permit.check(
        # user info
        {
            "key": email,
            "attributes": {
                "country": "England",
                "debug": "debug_yes"
            #    "role": "designer"
            }
        },
        # action
        "read",
        # resource info
        {
            "type": "HRS"
        }
    )
        
        logger.info(f"Permit.check decision for {email} (with inline attributes): {allowed}")
        return {
            "email": email, 
            "action": "read",
            "resource": "HRS", 
            # "inline_attributes_sent": user_object_for_check['attributes'],
            "allowed": allowed
        }
    except Exception as e_check:
        logger.exception(f"Error during permit.check for {email} (with inline attributes):")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Permission check failed: {str(e_check)}")
    
    
@router.get("/read_attributes_from_permitcloud")
async def read_permit_cloud_optimized_data(client: httpx.AsyncClient = Depends(get_http_client)):

    project_id = PROJECT_ID
    environment_id = ENV_ID
    org_id = ORG_ID 
    
    endpoint = f"/internal/opal_data/{org_id}/{project_id}/{environment_id}/optimized"
    return await make_permit_cloud_request(client, "GET", endpoint)


@router.get("/read_USER_attributes_from_local_opa_instance")
async def read_local_opa_smaug_data(client: httpx.AsyncClient = Depends(get_http_client)):
    """Reads the content of /data/smaug from the local OPA instance."""
    return await make_local_opa_request(client, "GET", "/v1/data/smaug")

@router.get("/read_ORG_attributes_from_local_opa_instance")
async def read_local_opa_smaug_data(client: httpx.AsyncClient = Depends(get_http_client)):
    """Reads the content of /data/smaug from the local OPA instance."""
    return await make_local_opa_request(client, "GET", "/v1/data/org")


@router.get("/read_policies_from_local_opa_instance")
async def read_local_opa_policies(client: httpx.AsyncClient = Depends(get_http_client)):
    """Reads all policies loaded into the local OPA instance."""
    return await make_local_opa_request(client, "GET", "/v1/policies")


@router.get("/read_opal_scope_from_permitcloud")
async def fetch_opal_scope_from_cloud(client: httpx.AsyncClient = Depends(get_http_client)):
    project_id = PROJECT_ID
    environment_id = ENV_ID
    endpoint = f"/projects/{project_id}/{environment_id}/opal_scope"
    return await make_permit_cloud_request(client, "GET", endpoint)



@router.put("/push_opa_config_to_permitcloud") 
async def push_opa_config_to_permitcloud_route(client: httpx.AsyncClient = Depends(get_http_client)):

    project_id = PROJECT_ID 
    environment_id = ENV_ID 

    external_data_source_url = f"http://web_app:8000{router.prefix}/read_current_db_attributes" 
    external_data_source_url_org = f"http://web_app:8000{router.prefix}/read_organization" 

    payload = {
        "data": {
            "entries": [
                {
                    "url": external_data_source_url,
                    "dst_path": "/smaug", # Destination path in OPA for this data
                    "periodic_update_interval": 60,
                    "config": {
                        "method": "get",
                        "fetch_on_boot": True,
                        "headers": {"Accept": "application/json"}
                    }
                },
                {
                    "url": external_data_source_url_org,
                    "dst_path": "/org",
                    "periodic_update_interval": 60,
                    "config": {
                        "method": "get",
                        "fetch_on_boot": True,
                        "headers": {"Accept": "application/json"}
                    }
                }
            ]
        }
    }
    endpoint = f"/projects/{project_id}/{environment_id}/opal_scope"
    return await make_permit_cloud_request(client, "PUT", endpoint, payload=payload)

    ##### CURRENT CONFIGURATION - keep updated for tracking - MVP #####
        #     curl -L -X PUT 'https://api.permit.io/v2/projects/2a4cdf901c5f48b6bd3f80f9579e92a9/9177328c79be438d9d3cfab3ec759fbc/opal_scope' \
        # -H 'Content-Type: application/json' \
        # -H 'Accept: application/json' \
        # -H 'Authorization: Bearer permit_key_DYCCSN4SZMeKyC37I879gJABnmSlpnvqavBbCMJGr50JoekDgECAQ6c7nKyZMmYwMpSgEAz51cJtfW7PaWtPbr' \
        # --data '{  "data": {    "entries": [
        #     {
        #         "url": "http://web_app:8000/opal/read_current_db_attributes",
        #         "dst_path": "/smaug",
        #         "periodic_update_interval": 60,
        #         "config": {
        #         "method": "get",
        #         "fetch_on_boot": true,
        #         "headers": {
        #             "Accept": "application/json"
        #         }        }      },
        #     {
        #         "url": "http://web_app:8000/opal/read_organization",
        #         "dst_path": "/org",
        #         "periodic_update_interval": 60,
        #         "config": {
        #         "method": "get",
        #         "fetch_on_boot": true,
        #         "headers": {
        #             "Accept": "application/json"
        #         }        }      }    ]  }}'

@router.put("/push_custom_policy_for_smaug_data") 
async def push_custom_policy_for_smaug_data_route():

    policy_id = "smaug_ro_hrs_access_policy"
    package_name = "permit.custom.smaug_rules"
    
    # accessible via OPA's data API at: data.{package_name.replace('.', '/')}.allow_read_engagement_for_english_users_from_smaug


    rego_code = f"""
        package permit.custom

        import input
        import data.smaug 
        import data.org 

        print_smaug_data {{
        print("DEBUG: data.smaug =", data.smaug)
        true
        }}

        print_smaug_debug {{
        print("DATA.SMAUG:", data.smaug)
        print("USER.KEY:", input.user.key)
        some i
        user_in_list := data.smaug[i]
        user_in_list.key == input.user.key
        print("MATCHED USER:", user_in_list)
        true
        }}

        get_user_from_smaug := user_obj {{
        some i
        user := data.smaug[i]
        user.key == input.user.key
        user_obj := user
        }}

        custom_user_attributes["country"] := country {{
        country := get_user_from_smaug.country
        }}

        custom_user_attributes["position"] := position {{
        position := get_user_from_smaug.position
        }}

        custom_user_attributes["debug_marker"] := "yes"

        user_is_romanian {{
        get_user_from_smaug.country == "romania"
        }}

        #default allow = false

        allow {{
        print_smaug_debug  # use this for logging
        input.action == "read"
        input.resource.type == "HRS"
        user_is_romanian
        }} 
        """
    print("--- Attempting to PUSH the following Rego to OPA ---")
    print(f"Policy ID: {policy_id}")
    print(f"Package Name: {package_name}")
    print(rego_code)
    print("----------------------------------------------------")

    opa_policy_url = f"http://permit_pdp:8181/v1/policies/{policy_id}"

    if not PERMIT_MANAGEMENT_API_KEY or "YOUR_FALLBACK_TOKEN" in PERMIT_MANAGEMENT_API_KEY or PERMIT_MANAGEMENT_API_KEY.startswith("permit_key_") is False:
        print("ERROR: PERMIT_MANAGEMENT_API_KEY is not properly configured for pushing policy.")
        raise HTTPException(status_code=500, detail="OPA token for policy push not configured or is a placeholder.")

    async with httpx.AsyncClient() as client:
        try:
            print(f"Attempting to DELETE existing policy (if any) at: {opa_policy_url}")
            delete_response = await client.delete(
                opa_policy_url,
                headers={"Authorization": f"Bearer {PERMIT_MANAGEMENT_API_KEY}"}
            )
            print(f"DELETE response status: {delete_response.status_code} (404 is OK if not found)")

            print(f"Attempting to PUT new policy to: {opa_policy_url}")
            response = await client.put(
                opa_policy_url,
                headers={
                    "Authorization": f"Bearer {PERMIT_MANAGEMENT_API_KEY}",
                    "Content-Type": "text/plain" 
                },
                content=rego_code 
            )

            print(f"PUT policy response status: {response.status_code}")
            response_body_text = response.text 

            response.raise_for_status()  

            try:
                response_data = response.json() 
                print(f"PUT policy response JSON: {json.dumps(response_data, indent=2)}")
                return {"status": "success", "policy_id": policy_id, "opa_response": response_data}
            except json.JSONDecodeError:
                print(f"PUT policy response (Non-JSON or empty): {response_body_text}")
                return {"status": "success", "policy_id": policy_id, "message": "Policy PUT to OPA successful", "raw_body": response_body_text}

        except httpx.HTTPStatusError as e:
            error_detail = f"OPA API HTTPStatusError: {e.response.status_code}"
            try:
                error_content = e.response.json()
                error_detail += f" - {json.dumps(error_content, indent=2)}"
            except json.JSONDecodeError:
                error_detail += f" - Body: {e.response.text}"
            print(f"ERROR pushing policy to OPA: {error_detail}")
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)
        except httpx.RequestError as e:
            print(f"Network error pushing policy to OPA: {e}")
            raise HTTPException(status_code=503, detail=f"Network error connecting to OPA: {str(e)}")