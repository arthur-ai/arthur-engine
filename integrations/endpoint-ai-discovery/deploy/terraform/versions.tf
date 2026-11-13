terraform {
  required_version = ">= 1.5"

  required_providers {
    # 6.33 is the first release with google_os_config_v2_policy_orchestrator_for_folder.
    google = {
      source  = "hashicorp/google"
      version = ">= 6.33, < 9"
    }
    http = {
      source  = "hashicorp/http"
      version = ">= 3.0, < 4"
    }
  }
}
