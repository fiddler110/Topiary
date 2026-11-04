moved {
  from = mist_site.ottawa
  to   = module.site["ottawa-01"].mist_site.this
}
moved {
  from = mist_site_setting.ottawa
  to   = module.site["ottawa-01"].mist_site_setting.this
}
moved {
  from = mist_site.toronto
  to   = module.site["toronto-01"].mist_site.this
}
moved {
  from = mist_site_setting.toronto
  to   = module.site["toronto-01"].mist_site_setting.this
}
moved {
  from = mist_site.montreal
  to   = module.site["montreal-01"].mist_site.this
}
moved {
  from = mist_site_setting.montreal
  to   = module.site["montreal-01"].mist_site_setting.this
}
moved {
  from = mist_device_gateway.ottawa
  to   = module.gateway["ottawa-01"].mist_device_gateway.this
}
