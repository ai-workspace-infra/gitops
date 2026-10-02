require 'minitest/autorun'
require 'yaml'
require 'tempfile'
require 'open3'

class IdentityManifestTest < Minitest::Test
  ROOT = File.expand_path('..', __dir__)
  def setup
    @doc = YAML.safe_load(File.read("#{ROOT}/resources/svc.plus/uat/iam/identity-integrations.yaml"))
  end

  def validate(doc)
    Tempfile.create(['iam-test-', '.yaml']) do |file|
      file.write(YAML.dump(doc)); file.flush
      out, err, status = Open3.capture3('bash', "#{ROOT}/scripts/validate-iam-integrations.sh", file.path)
      return status.success?, out + err
    end
  end

  def test_valid_manifest
    ok, output = validate(@doc)
    assert ok, output
  end

  def test_reject_invalid_contracts
    mutations = {
      missing_provider: ->(d) { d['spec']['integrations'].pop },
      duplicate_provider: ->(d) { d['spec']['integrations'][1] = d['spec']['integrations'][0] },
      invalid_protocol: ->(d) { d['spec']['integrations'][0]['flows'][0]['protocol'] = 'password' },
      saml_despite_oidc: ->(d) { d['spec']['integrations'][0]['flows'][0]['protocol'] = 'saml' },
      missing_saml_reason: ->(d) { d['spec']['integrations'][1]['flows'][0].delete('selection_reason') },
      false_oidc: ->(d) { d['spec']['integrations'][0]['flows'][0]['oidc_supported'] = false },
      string_boolean: ->(d) { d['spec']['integrations'][0]['flows'][0]['oidc_supported'] = 'true' },
      secret: ->(d) { d['spec']['integrations'][0]['flows'][0]['client_secret'] = 'FAKE' },
      top_level_secret: ->(d) { d['api_token'] = 'FAKE' },
      cross_environment: ->(d) { d['spec']['integrations'][0]['flows'][0]['vault_ref'].sub!('/uat/', '/prod/') },
      wrong_provider_ref: ->(d) { d['spec']['integrations'][0]['flows'][0]['vault_ref'].sub!('/gcp/', '/aws/') },
      traversal_ref: ->(d) { d['spec']['integrations'][0]['flows'][0]['vault_ref'].sub!('/workforce/', '/../') },
      cross_environment_api: ->(d) { d['spec']['integrations'][2]['flows'][1]['vault_ref'].sub!('/uat/', '/prod/') },
      http_issuer: ->(d) { d['spec']['issuer'] = 'http://example.test' },
      malformed_issuer: ->(d) { d['spec']['issuer'] = 'https://' },
      http_evidence: ->(d) { d['spec']['integrations'][0]['flows'][0]['capability_evidence_url'] = 'http://example.test' },
      wildcard_callback: ->(d) { d['spec']['integrations'][5]['flows'][0]['redirect_uris'] = ['https://*.example.test/callback'] },
      relative_callback: ->(d) { d['spec']['integrations'][5]['flows'][0]['redirect_uris'] = ['/callback'] },
      duplicate_purpose: ->(d) { d['spec']['integrations'][0]['flows'][1]['purpose'] = 'workforce' },
      invalid_environment: ->(d) { d['metadata']['environment'] = 'dev' },
      empty_flows: ->(d) { d['spec']['integrations'][0]['flows'] = [] },
      missing_api_reason: ->(d) { d['spec']['integrations'][2]['flows'][1].delete('selection_reason') }
    }
    mutations.each do |name, change|
      doc = Marshal.load(Marshal.dump(@doc)); change.call(doc)
      ok, output = validate(doc)
      refute ok, "#{name} unexpectedly passed: #{output}"
    end
  end
end
